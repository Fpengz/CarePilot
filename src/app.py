import asyncio
from datetime import date, datetime, timezone
from typing import cast
from uuid import uuid4

import streamlit as st

from dietary_guardian.agents.hawker_vision import HawkerVisionModule
from dietary_guardian.agents.provider_factory import ModelProvider
from dietary_guardian.config.runtime import AppConfig, LocalModelProfile
from dietary_guardian.models.medication import MedicationRegimen, TimingType
from dietary_guardian.models.user import (
    MedicalCondition,
    MealSlot,
    MealScheduleWindow,
    Medication,
    UserProfile,
    UserRole,
)
from dietary_guardian.services.dashboard_service import (
    build_analytics_summary,
    build_role_medication_view,
    build_role_report_advice_view,
)
from dietary_guardian.services.medication_service import (
    compute_mcr,
    generate_daily_reminders,
    mark_meal_confirmation,
)
from dietary_guardian.services.notification_service import dispatch_reminder
from dietary_guardian.services.recommendation_service import generate_recommendation
from dietary_guardian.services.report_parser_service import (
    build_clinical_snapshot,
    parse_report_input,
)
from dietary_guardian.services.repository import SQLiteRepository
from dietary_guardian.services.social_service import SocialService
from dietary_guardian.services.upload_service import build_image_input
from dietary_guardian.models.report import ReportInput
from dietary_guardian.logging_config import get_logger, setup_logging

setup_logging("dietary-guardian-app")
logger = get_logger(__name__)

st.set_page_config(page_title="Dietary Guardian SG", page_icon="🍲", layout="wide")


def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


if "social_service" not in st.session_state:
    st.session_state.social_service = SocialService()
    st.session_state.social_service.register_block("Blk 105", "123")
    st.session_state.social_service.register_block("Blk 106", "123")

if "repository" not in st.session_state:
    st.session_state.repository = SQLiteRepository("dietary_guardian.db")

if "meal_history_meta" not in st.session_state:
    st.session_state.meal_history_meta = []

if "latest_snapshot" not in st.session_state:
    st.session_state.latest_snapshot = None

app_config = AppConfig()
repo: SQLiteRepository = st.session_state.repository

st.sidebar.title("Session Controls")
role = cast(
    UserRole,
    st.sidebar.selectbox(
        "Active role",
        options=["patient", "caregiver", "clinician"],
        index=0,
    ),
)
runtime_mode = st.sidebar.radio("Model runtime", options=["cloud", "local"], index=0)
notification_channels = st.sidebar.multiselect(
    "Notification channels",
    options=["in_app", "push", "telegram", "whatsapp", "wechat"],
    default=["in_app", "push"],
)

selected_provider = ModelProvider.GEMINI.value
selected_model_name = app_config.models.primary_model
local_profile: LocalModelProfile | None = None

if runtime_mode == "cloud":
    selected_provider = st.sidebar.selectbox(
        "Cloud provider",
        options=[ModelProvider.GEMINI.value, ModelProvider.TEST.value],
        index=0,
    )
    selected_model_name = st.sidebar.text_input("Cloud model name", value=app_config.models.primary_model)
else:
    profile_keys = list(app_config.local_models.profiles.keys())
    selected_profile = st.sidebar.selectbox("Local model profile", options=profile_keys)
    base = app_config.local_models.profiles[selected_profile]
    selected_model_name = st.sidebar.text_input("Local model override", value=base.model_name)
    selected_base_url = st.sidebar.text_input("Local base URL override", value=base.base_url)
    local_profile = LocalModelProfile(
        id=base.id,
        provider=base.provider,
        model_name=selected_model_name,
        base_url=selected_base_url,
        api_key_env=base.api_key_env,
        enabled=base.enabled,
    )
    selected_provider = base.provider

st.sidebar.caption(f"Active runtime: `{selected_provider}` / `{selected_model_name}`")
logger.info(
    "app_session_start role=%s runtime_mode=%s provider=%s model=%s channels=%s",
    role,
    runtime_mode,
    selected_provider,
    selected_model_name,
    notification_channels,
)

mr_tan = UserProfile(
    id="user_001",
    name="Mr. Tan",
    age=68,
    conditions=[
        MedicalCondition(name="Diabetes", severity="High"),
        MedicalCondition(name="Hypertension", severity="Medium"),
    ],
    medications=[Medication(name="Warfarin", dosage="5mg")],
    role=role,
    meal_schedule=[
        MealScheduleWindow(slot="breakfast", start_time="07:00", end_time="09:00"),
        MealScheduleWindow(slot="lunch", start_time="12:00", end_time="14:00"),
        MealScheduleWindow(slot="dinner", start_time="18:00", end_time="20:00"),
    ],
)

st.title("Dietary Guardian SG")
st.subheader("Medication + Meal Intelligence")

if role == "clinician":
    st.write("### Clinician: Medication Regimen Editor")
    with st.form("regimen_form"):
        med_name = st.text_input("Medication name", value="Metformin")
        dose = st.text_input("Dosage", value="500mg")
        timing = cast(
            TimingType,
            st.selectbox("Timing type", ["pre_meal", "post_meal", "fixed_time"]),
        )
        slot_scope = cast(
            list[MealSlot],
            st.multiselect(
                "Meal slots",
                ["breakfast", "lunch", "dinner", "snack"],
                default=["lunch"],
            ),
        )
        offset = st.number_input("Offset minutes", min_value=0, max_value=180, value=30)
        fixed_time = st.text_input("Fixed time (HH:MM)", value="22:00")
        submitted = st.form_submit_button("Save regimen")
    if submitted:
        regimen = MedicationRegimen(
            id=str(uuid4()),
            user_id=mr_tan.id,
            medication_name=med_name,
            dosage_text=dose,
            timing_type=timing,
            offset_minutes=int(offset),
            slot_scope=slot_scope,
            fixed_time=fixed_time if timing == "fixed_time" else None,
        )
        repo.save_medication_regimen(regimen)
        logger.info(
            "app_regimen_saved user_id=%s regimen_id=%s medication=%s timing=%s",
            mr_tan.id,
            regimen.id,
            regimen.medication_name,
            regimen.timing_type,
        )
        st.success("Regimen saved")

st.write("### Daily Reminder Generation")
example_regimens = [
    MedicationRegimen(
        id="demo-pre",
        user_id=mr_tan.id,
        medication_name="Metformin",
        dosage_text="500mg",
        timing_type="pre_meal",
        offset_minutes=30,
        slot_scope=["lunch"],
    ),
    MedicationRegimen(
        id="demo-post",
        user_id=mr_tan.id,
        medication_name="Amlodipine",
        dosage_text="5mg",
        timing_type="post_meal",
        offset_minutes=15,
        slot_scope=["dinner"],
    ),
]

if st.button("Generate Today Reminders"):
    reminders = generate_daily_reminders(mr_tan, example_regimens, date.today())
    for reminder in reminders:
        repo.save_reminder_event(reminder)
        dispatch_reminder(reminder, notification_channels, force_push_fail=False)
    logger.info("app_reminders_generated user_id=%s count=%s", mr_tan.id, len(reminders))
    st.success(f"Generated {len(reminders)} reminders")

all_reminders = repo.list_reminder_events(mr_tan.id)
if all_reminders:
    st.write("### Reminders")
    for event in all_reminders[-10:]:
        st.write(
            f"- {event.medication_name} {event.dosage_text} at {event.scheduled_at.isoformat()} [{event.status}]"
        )
    pending = [e for e in all_reminders if e.status == "sent"]
    if pending and role == "patient":
        options = {f"{e.medication_name} @ {e.scheduled_at.strftime('%H:%M')} ({e.id[:8]})": e.id for e in pending}
        selected = st.selectbox("Confirm meal for reminder", list(options.keys()))
        col_a, col_b = st.columns(2)
        if col_a.button("Meal Confirmed: Yes"):
            mark_meal_confirmation(options[selected], True, datetime.now(timezone.utc), repo)
            logger.info("app_meal_confirmed_yes reminder_id=%s", options[selected])
            st.success("Reminder acknowledged")
        if col_b.button("Meal Confirmed: No"):
            mark_meal_confirmation(options[selected], False, datetime.now(timezone.utc), repo)
            logger.info("app_meal_confirmed_no reminder_id=%s", options[selected])
            st.warning("Reminder marked missed")

if role == "patient":
    st.write("### Meal Capture")
    uploaded_file = st.file_uploader("Upload meal photo", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=False)
    camera_file = st.camera_input("Or take live photo")
    if st.button("Analyze Meal Image", type="primary"):
        image_input, error = build_image_input(uploaded_file, camera_file)
        if error:
            logger.warning("app_image_input_error error=%s", error)
            st.error(error)
        elif image_input is not None:
            module = HawkerVisionModule(
                provider=selected_provider,
                model_name=selected_model_name,
                local_profile=local_profile,
            )
            result, record = run_async(module.analyze_and_record(image_input, mr_tan.id))
            repo.save_meal_record(record)
            logger.info(
                "app_meal_analyzed user_id=%s record_id=%s dish=%s",
                mr_tan.id,
                record.id,
                record.meal_state.dish_name,
            )
            st.session_state.meal_history_meta.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": record.source,
                    "dish_name": record.meal_state.dish_name,
                    "multi_item_count": record.multi_item_count,
                }
            )
            st.json(result.model_dump())

st.write("### Health Report Parsing")
report_text = st.text_area("Paste report text", value="HbA1c 7.1 LDL 4.2")
report_upload = st.file_uploader("Upload report PDF (optional)", type=["pdf"], key="report_pdf")
if st.button("Parse Report and Build Snapshot"):
    report_input = ReportInput(
        source="pdf" if report_upload else "pasted_text",
        content_bytes=report_upload.getvalue() if report_upload else None,
        text=report_text if not report_upload else None,
    )
    readings = parse_report_input(report_input)
    snapshot = build_clinical_snapshot(readings)
    logger.info(
        "app_report_parsed source=%s readings=%s risk_flags=%s",
        report_input.source,
        len(readings),
        snapshot.risk_flags,
    )
    st.session_state.latest_snapshot = snapshot
    repo.save_biomarker_readings(mr_tan.id, readings)
    st.json(snapshot.model_dump())

meal_records = repo.list_meal_records(mr_tan.id)
if meal_records and st.session_state.latest_snapshot is not None:
    latest_record = meal_records[-1]
    recommendation = generate_recommendation(latest_record, st.session_state.latest_snapshot, mr_tan)
    repo.save_recommendation(mr_tan.id, recommendation.model_dump())
    logger.info(
        "app_recommendation_generated user_id=%s safe=%s advice_items=%s",
        mr_tan.id,
        recommendation.safe,
        len(recommendation.localized_advice),
    )
    role_view = build_role_report_advice_view(role, recommendation)
    st.write("### Personalized Advice")
    st.write(role_view["message"])
    if recommendation.blocked_reason:
        st.warning(recommendation.blocked_reason)

st.divider()
st.write("### Analytics Dashboard")
metrics = compute_mcr(all_reminders)
summary = build_analytics_summary(metrics, all_reminders)
view_stats = build_role_medication_view(role, all_reminders)
col1, col2, col3 = st.columns(3)
col1.metric("MCR", f"{summary['mcr']:.2f}")
col2.metric("Reminders Sent", int(summary["reminders_sent"]))
col3.metric("Acknowledged", int(summary["acknowledged"]))
st.json(view_stats)

st.write("### Session Meal Metadata")
st.json(st.session_state.meal_history_meta)

st.write("### Kampong Spirit Challenge")
leaderboard = st.session_state.social_service.get_leaderboard("main_challenge")
for block_id, score in leaderboard:
    st.write(f"{block_id}: {score} points")
