import gradio as gr
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from agents.chat_agent import ChatAgent
from agents.audio_agent import AudioAgent
from agents.search_agent import SearchAgent
from agents.health_tracker import HealthTracker
from routes import QueryRouter
from ingestion.usermed_ingest import (
    user_med_db,
    prescription_parser,
    TIMING_LABEL_TO_SLOT,
    SLOT_TO_LABEL,
    TIMING_SLOTS,
)

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
CHAT_MODEL_ID = os.environ.get("CHAT_MODEL_ID", "aisingapore/Gemma-SEA-LION-v4-27B-IT")

# --- Initialise agents ---
search_agent = SearchAgent(max_results=3)
router = QueryRouter(search_agent)
chat_agent = ChatAgent(model_id=CHAT_MODEL_ID, router=router)
health_tracker = HealthTracker(
    session_id="default",
    client=chat_agent.client,
    model_id=CHAT_MODEL_ID,
)
audio_agent = AudioAgent()
# To enable MERaLiON local transcription, uncomment:
# audio_agent.load_model()

TRANSCRIPTION_BACKENDS = {
    "Groq Whisper (cloud)": audio_agent.transcribe_groq,
    "MERaLiON (local)": audio_agent.transcribe,
}

TIMING_LABELS = list(TIMING_LABEL_TO_SLOT.keys())

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
css = """
#chatbot-col { position: relative; }
#send-btn {
    min-width: 44px; max-width: 44px; height: 44px;
    border-radius: 50%; padding: 0; font-size: 18px;
}
#plus-btn {
    min-width: 44px; max-width: 44px; height: 44px;
    border-radius: 50%; padding: 0; font-size: 22px;
}
#popup-menu {
    border-radius: 14px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.18);
    padding: 8px 0;
    margin-bottom: 6px;
    max-width: 260px;
}
#popup-menu .gr-button {
    justify-content: flex-start;
    border-radius: 8px;
    border: none;
    background: transparent;
    font-size: 15px;
    padding: 10px 18px;
    width: 100%;
    text-align: left;
}
#popup-menu .gr-button:hover { background: rgba(128,128,128,0.15); }
#audio-panel, #image-panel {
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 6px;
}
.med-table { font-size: 14px; }
"""

# ---------------------------------------------------------------------------
# Medication tab helpers
# ---------------------------------------------------------------------------

MED_HEADERS = ["ID", "Medicine", "Dose / Notes", "Schedule", "Added"]


def _refresh_med_table():
    return user_med_db.to_display_rows()


def parse_prescription(text: str):
    if not text.strip():
        return [], "⚠ Please paste some prescription text first."
    try:
        entries = prescription_parser.parse(text)
    except ValueError as e:
        return [], f"❌ Parse error: {e}"
    if not entries:
        return [], "⚠ No medications found in the text."
    rows = []
    for e in entries:
        labels = ", ".join(SLOT_TO_LABEL[s] for s in e["timing"]) or "—"
        rows.append([e["medicine_name"], e["dose_notes"] or "—", labels])
    return rows, f"✅ Found {len(entries)} medication(s). Review then click **Parse & Save All**."


def save_all_parsed(text: str):
    if not text.strip():
        return _refresh_med_table(), "⚠ No text to parse."
    try:
        entries = prescription_parser.parse(text)
    except ValueError as e:
        return _refresh_med_table(), f"❌ Parse error: {e}"
    if not entries:
        return _refresh_med_table(), "⚠ Nothing to save."
    for e in entries:
        user_med_db.add_medication(e["medicine_name"], e["timing"], e["dose_notes"])
    return _refresh_med_table(), f"✅ Saved {len(entries)} medication(s)."


def add_manual(name: str, dose: str, timing_labels: list):
    if not name.strip():
        return _refresh_med_table(), "⚠ Medicine name is required."
    slots = [TIMING_LABEL_TO_SLOT[lbl] for lbl in timing_labels if lbl in TIMING_LABEL_TO_SLOT]
    user_med_db.add_medication(name.strip(), slots, dose.strip())
    return _refresh_med_table(), f"✅ Added '{name.strip()}'."


def delete_med(row_id_str: str):
    try:
        row_id = int(row_id_str)
    except (ValueError, TypeError):
        return _refresh_med_table(), "⚠ Enter a valid numeric ID from the table."
    deleted = user_med_db.delete_medication(row_id)
    msg = f"✅ Deleted ID {row_id}." if deleted else f"⚠ No row with ID {row_id}."
    return _refresh_med_table(), msg


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="SEA-LION Health Assistant") as demo:

    with gr.Tabs():

        # ====================================================================
        # Tab 1 — Chat
        # ====================================================================
        with gr.Tab("💬 Chat"):
            gr.Markdown("# Chat with SEA-LION")

            chatbot = gr.Chatbot(height=500, elem_id="chatbot-col")

            # Popup menu
            with gr.Column(visible=False, elem_id="popup-menu") as popup_menu:
                audio_opt_btn = gr.Button("🎤  Record Audio")
                image_opt_btn = gr.Button("🖼️  Upload Image")

            # Audio sub-panel
            with gr.Column(visible=False, elem_id="audio-panel") as audio_panel:
                mic_recorder = gr.Audio(sources=["microphone"], type="numpy", label="Record your message")
                transcription_selector = gr.Radio(
                    choices=list(TRANSCRIPTION_BACKENDS.keys()),
                    value="Groq Whisper (cloud)",
                    label="Transcription backend",
                )

            # Image sub-panel
            with gr.Column(visible=False, elem_id="image-panel") as image_panel:
                image_upload = gr.Image(type="pil", label="Upload an image")
                gr.Markdown("_Image input is not yet connected to the model._")

            # Input row
            with gr.Row(equal_height=True):
                plus_btn   = gr.Button("＋", elem_id="plus-btn", scale=0)
                text_input = gr.Textbox(
                    show_label=False, placeholder="Ask anything...",
                    container=False, scale=8, lines=1,
                )
                send_btn = gr.Button("➤", elem_id="send-btn", scale=0, variant="primary")

            track_btn = gr.Button("📍 [TRACK] Log a metric", variant="secondary", size="sm")

            menu_open = gr.State(False)

            def toggle_menu(open):
                new_open = not open
                return gr.update(visible=new_open), new_open, gr.update(visible=False), gr.update(visible=False)

            plus_btn.click(toggle_menu, [menu_open], [popup_menu, menu_open, audio_panel, image_panel])

            def show_audio():
                return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), False

            audio_opt_btn.click(show_audio, [], [popup_menu, audio_panel, image_panel, menu_open])

            def show_image():
                return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), False

            image_opt_btn.click(show_image, [], [popup_menu, audio_panel, image_panel, menu_open])

            def handle_text(message, history):
                _, history = chat_agent.chat(message, history)
                return "", history

            def handle_audio(audio_data, history, backend_name):
                if audio_data is None:
                    return history
                transcribe_fn = TRANSCRIPTION_BACKENDS.get(backend_name, audio_agent.transcribe_groq)
                _, history = chat_agent.chat("", history, audio_input=audio_data, transcribe_fn=transcribe_fn)
                return history

            text_input.submit(handle_text, [text_input, chatbot], [text_input, chatbot])
            send_btn.click(handle_text, [text_input, chatbot], [text_input, chatbot])
            mic_recorder.stop_recording(handle_audio, [mic_recorder, chatbot, transcription_selector], [chatbot])
            track_btn.click(lambda t: "[TRACK] " if not t.startswith("[TRACK]") else t, [text_input], [text_input])

        # ====================================================================
        # Tab 2 — My Medications
        # ====================================================================
        with gr.Tab("💊 My Medications"):
            gr.Markdown("## My Medication Schedule")
            gr.Markdown(
                "Paste your doctor's prescription or advice below — "
                "AI will extract the medicine names and timings. "
                "Or add medications manually using the form."
            )

            # ── AI Parse section ──────────────────────────────────────────
            with gr.Group():
                gr.Markdown("### 📋 Parse from Prescription / Doctor's Note")
                prescription_input = gr.Textbox(
                    lines=5,
                    placeholder=(
                        "Paste prescription text here in any language, e.g.\n"
                        "Metformin 500mg twice daily after meals.\n"
                        "二甲双胍 500mg 三餐后服用。\n"
                        "Amlodipine 5mg once daily after dinner."
                    ),
                    label="Prescription / Doctor's Advice",
                )
                with gr.Row():
                    parse_btn    = gr.Button("🔍 Preview", variant="secondary")
                    save_all_btn = gr.Button("💾 Parse & Save All", variant="primary")

                parse_status  = gr.Markdown("")
                parse_preview = gr.Dataframe(
                    headers=["Medicine", "Dose / Notes", "Schedule"],
                    datatype=["str", "str", "str"],
                    label="Parsed Preview",
                    interactive=False,
                    visible=False,
                    elem_classes=["med-table"],
                )

            # ── Manual add section ────────────────────────────────────────
            with gr.Group():
                gr.Markdown("### ✏️ Add Manually")
                with gr.Row():
                    manual_name = gr.Textbox(label="Medicine Name", placeholder="e.g. Metformin 500mg")
                    manual_dose = gr.Textbox(label="Dose / Notes (optional)", placeholder="e.g. 1 tablet")
                manual_timing = gr.CheckboxGroup(choices=TIMING_LABELS, label="When to take")
                with gr.Row():
                    add_btn    = gr.Button("➕ Add Medication", variant="primary")
                    manual_msg = gr.Markdown("")

            # ── Current medications table ─────────────────────────────────
            gr.Markdown("### 📅 Current Schedule")
            med_table = gr.Dataframe(
                value=_refresh_med_table,
                headers=MED_HEADERS,
                datatype=["number", "str", "str", "str", "str"],
                label="My Medications",
                interactive=False,
                elem_classes=["med-table"],
            )

            # ── Delete section ────────────────────────────────────────────
            with gr.Row():
                delete_id_input = gr.Textbox(
                    label="Delete by ID",
                    placeholder="Enter ID number from table above",
                    scale=3,
                )
                delete_btn = gr.Button("🗑 Delete", variant="stop", scale=1)
            delete_msg = gr.Markdown("")

            # ── Events ───────────────────────────────────────────────────

            def on_parse(text):
                rows, msg = parse_prescription(text)
                return gr.update(value=rows, visible=len(rows) > 0), msg

            parse_btn.click(
                on_parse,
                inputs=[prescription_input],
                outputs=[parse_preview, parse_status],
            )

            def on_save_all(text):
                table_data, msg = save_all_parsed(text)
                return table_data, msg, gr.update(visible=False, value=[])

            save_all_btn.click(
                on_save_all,
                inputs=[prescription_input],
                outputs=[med_table, parse_status, parse_preview],
            )

            def on_add(name, dose, timing_labels):
                table_data, msg = add_manual(name, dose, timing_labels)
                return table_data, msg, "", "", []

            add_btn.click(
                on_add,
                inputs=[manual_name, manual_dose, manual_timing],
                outputs=[med_table, manual_msg, manual_name, manual_dose, manual_timing],
            )

            def on_delete(row_id_str):
                table_data, msg = delete_med(row_id_str)
                return table_data, msg, ""

            delete_btn.click(
                on_delete,
                inputs=[delete_id_input],
                outputs=[med_table, delete_msg, delete_id_input],
            )


        # ====================================================================
        # Tab 3 — Health Dashboard
        # ====================================================================
        with gr.Tab("📊 Health Dashboard"):
            gr.Markdown("## Health Metrics Dashboard")
            gr.Markdown(
                "Select a date range and click **Generate Chart** to visualise metrics "
                "you have logged using `[TRACK]` in the chat.  \n"
                "Example: `[TRACK] weight 80 kg` · `[TRACK] bp 135/88 mmHg` · `[TRACK] glucose 7.5 mmol/L`"
            )

            with gr.Row():
                _default_end   = datetime.now().strftime("%Y-%m-%d")
                _default_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                dash_start = gr.Textbox(
                    label="Start date (YYYY-MM-DD)",
                    value=_default_start,
                    scale=2,
                )
                dash_end = gr.Textbox(
                    label="End date (YYYY-MM-DD)",
                    value=_default_end,
                    scale=2,
                )
                dash_btn = gr.Button("📈 Generate Chart", variant="primary", scale=1)

            dash_plot = gr.Plot(label="Metrics Over Time")

            gr.Markdown("### Raw [TRACK] entries in range")
            dash_table = gr.Dataframe(
                headers=["Date / Time", "Message"],
                datatype=["str", "str"],
                label="Logged entries",
                interactive=False,
            )

            def on_generate_chart(start, end):
                from datetime import datetime, timedelta
                try:
                    datetime.strptime(start, "%Y-%m-%d")
                    datetime.strptime(end, "%Y-%m-%d")
                except ValueError:
                    import matplotlib.pyplot as plt
                    fig, ax = plt.subplots()
                    ax.text(0.5, 0.5, "Invalid date format. Use YYYY-MM-DD.",
                            ha="center", va="center", transform=ax.transAxes)
                    ax.set_axis_off()
                    return fig, []
                fig = health_tracker.build_chart(start, end)
                raw = health_tracker.get_raw_entries(start, end)
                table_rows = [
                    [r["created_at"][:16].replace("T", " "), r["content"]]
                    for r in raw
                ]
                return fig, table_rows

            dash_btn.click(
                on_generate_chart,
                inputs=[dash_start, dash_end],
                outputs=[dash_plot, dash_table],
            )


if __name__ == "__main__":
    if chat_agent.api_key is None or chat_agent.api_key == "YOUR_API_KEY":
        print("WARNING: API key not set. Please set the SEALION_API environment variable in your .env file.")
    demo.launch(css=css)



