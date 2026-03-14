"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import { ChatSidebar } from "./components/chat-sidebar";
import { ChatHeader } from "@/components/chat/chat-header";
import { MessageList } from "@/components/chat/message-list";
import { StickyComposer } from "@/components/chat/sticky-composer";
import { type Message, type MessageView } from "./components/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend";

const displayFont = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "600", "700"],
});

const bodyFont = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
});

const makeId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const normalizeMessage = (message: Partial<Message>, index: number): Message => ({
  id: message.id ?? `${Date.now()}-${index}-${Math.random().toString(16).slice(2)}`,
  role: message.role ?? "assistant",
  content: message.content ?? "",
  emotion: message.emotion,
  tag: message.tag,
  mealProposal: message.mealProposal,
  title: message.title,
  explanation: message.explanation,
  reasoning: message.reasoning,
  confidence: message.confidence,
});

const deriveMessageView = (message: Message): MessageView => {
  if (message.role === "user") {
    return { ...message, kind: "plain" };
  }

  const lower = message.content.toLowerCase();
  let kind: MessageView["kind"] = "plain";
  let title: string | undefined;
  let explanation: string | undefined;

  if (message.tag === "error" || lower.startsWith("⚠")) {
    kind = "proactive_alert";
    title = "Attention needed";
    explanation = "The companion hit an interruption and paused the response.";
  } else if (
    message.mealProposal ||
    lower.includes("meal analysis") ||
    lower.includes("macros") ||
    lower.includes("calories")
  ) {
    kind = "meal_analysis";
    title = "Meal analysis summary";
    explanation = "Highlights from your latest meal entry and nutrition signals.";
  } else if (
    lower.includes("trend") ||
    lower.includes("over time") ||
    lower.includes("week") ||
    lower.includes("pattern")
  ) {
    kind = "trend_insight";
    title = "Trend insight";
    explanation = "Comparing recent check-ins to your baseline for consistency.";
  } else if (
    lower.includes("recommend") ||
    lower.includes("suggest") ||
    lower.includes("consider")
  ) {
    kind = "recommendation";
    title = "Recommended next step";
    explanation = "A focused action aligned to your care priorities.";
  } else if (
    lower.includes("clarify") ||
    lower.includes("follow up") ||
    lower.trim().endsWith("?")
  ) {
    kind = "follow_up";
    title = "Quick clarification";
    explanation = "One detail helps keep guidance precise.";
  }

  return {
    ...message,
    kind,
    title: message.title ?? title,
    explanation: message.explanation ?? explanation,
    reasoning: message.reasoning,
    confidence: message.confidence,
  };
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingMs, setRecordingMs] = useState(0);
  const [streamDraft, setStreamDraft] = useState("");
  const [proposalLoadingId, setProposalLoadingId] = useState<string | null>(null);
  const [streamNotice, setStreamNotice] = useState<string | null>(null);
  const [audioNotice, setAudioNotice] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamBufferRef = useRef("");
  const streamFlushRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/chat/history`)
      .then((r) => r.json())
      .then((data) => {
        const history = Array.isArray(data.messages) ? data.messages : [];
        setMessages(history.map((m: Partial<Message>, idx: number) => normalizeMessage(m, idx)));
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    const behavior = streamDraft ? "auto" : "smooth";
    bottomRef.current?.scrollIntoView({ behavior });
  }, [messages, streamDraft]);

  useEffect(() => {
    return () => {
      if (streamFlushRef.current) {
        clearTimeout(streamFlushRef.current);
        streamFlushRef.current = null;
      }
    };
  }, []);

  const messageViews = useMemo(() => messages.map((m) => deriveMessageView(m)), [messages]);

  const handleSend = async () => {
    const messageText = input.trim();
    if (!messageText || loading) return;

    setInput("");
    setLoading(true);
    setStreamDraft("");
    setStreamNotice(null);
    setAudioNotice(null);
    streamBufferRef.current = "";
    setMessages((prev) => [
      ...prev,
      { id: makeId(), role: "user", content: messageText },
      { id: makeId(), role: "assistant", content: "" },
    ]);

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: messageText }),
      });
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      const flushStream = () => {
        setStreamDraft(streamBufferRef.current);
        streamFlushRef.current = null;
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            const { event, data } = payload;
            if (event === "emotion") {
              setMessages((prev) => {
                const msgs = [...prev];
                const userIdx = msgs.length - 2;
                if (userIdx >= 0 && msgs[userIdx].role === "user") {
                  msgs[userIdx] = {
                    ...msgs[userIdx],
                    emotion: { label: data.emotion, score: data.score },
                  };
                }
                return msgs;
              });
            }
            if (event === "meal_proposed") {
              setMessages((prev) => {
                const msgs = [...prev];
                const idx = msgs.length - 1;
                if (idx >= 0 && msgs[idx].role === "assistant") {
                  msgs[idx] = {
                    ...msgs[idx],
                    content: data.prompt ?? "I can log this meal. Confirm?",
                    mealProposal: {
                      proposalId: data.proposal_id,
                      mealText: data.meal_text,
                    },
                  };
                }
                return msgs;
              });
            }
            if (event === "token") {
              streamBufferRef.current += data.text;
              if (!streamFlushRef.current) {
                streamFlushRef.current = setTimeout(flushStream, 80);
              }
            }
            if (event === "error") {
              setStreamNotice(data.message || "Streaming response interrupted.");
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = {
                  ...msgs[msgs.length - 1],
                  role: "assistant",
                  content: "⚠ " + (data.message || "Request failed."),
                  tag: "error",
                };
                return msgs;
              });
            }
            if (event === "done") {
              if (streamFlushRef.current) {
                clearTimeout(streamFlushRef.current);
                streamFlushRef.current = null;
              }
              if (streamBufferRef.current) {
                const finalText = streamBufferRef.current;
                streamBufferRef.current = "";
                setMessages((prev) => {
                  const msgs = [...prev];
                  msgs[msgs.length - 1] = {
                    ...msgs[msgs.length - 1],
                    content: finalText,
                  };
                  return msgs;
                });
                setStreamDraft("");
              }
            }
          } catch {
            // ignore incomplete chunk
          }
        }
      }
    } catch {
      setStreamNotice("Unable to reach the server. Check backend status.");
      setMessages((prev) => {
        const msgs = [...prev];
        msgs[msgs.length - 1] = {
          ...msgs[msgs.length - 1],
          role: "assistant",
          content: "⚠ Could not reach the server. Is the backend running?",
          tag: "error",
        };
        return msgs;
      });
    } finally {
      if (streamFlushRef.current) {
        clearTimeout(streamFlushRef.current);
        streamFlushRef.current = null;
      }
      if (streamBufferRef.current) {
        const finalText = streamBufferRef.current;
        streamBufferRef.current = "";
        setMessages((prev) => {
          const msgs = [...prev];
          msgs[msgs.length - 1] = {
            ...msgs[msgs.length - 1],
            content: finalText,
          };
          return msgs;
        });
        setStreamDraft("");
      }
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleMealProposal = async (proposalId: string, action: "confirm" | "skip") => {
    if (proposalLoadingId) return;
    setProposalLoadingId(proposalId);
    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/meal/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ proposal_id: proposalId, action }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail || "Could not update meal proposal.");
      }
      setMessages((prev) => {
        const msgs = [...prev];
        const idx = msgs.findIndex((m) => m.mealProposal?.proposalId === proposalId);
        if (idx >= 0) {
          msgs[idx] = {
            ...msgs[idx],
            content: action === "confirm" ? body.message || "Meal logged." : "Skipped logging this meal.",
            mealProposal: undefined,
          };
        }
        if (body.assistant_followup) {
          msgs.push({
            id: makeId(),
            role: "assistant",
            content: body.assistant_followup,
          });
        }
        return msgs;
      });
    } catch {
      setMessages((prev) => {
        const msgs = [...prev];
        const idx = msgs.findIndex((m) => m.mealProposal?.proposalId === proposalId);
        if (idx >= 0) {
          msgs[idx] = {
            ...msgs[idx],
            content: "⚠ Could not update the meal log. Please try again.",
            tag: "error",
            mealProposal: undefined,
          };
        }
        return msgs;
      });
    } finally {
      setProposalLoadingId(null);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const prependTrack = () => {
    setInput((prev) => (prev.startsWith("[TRACK]") ? prev : "[TRACK] " + prev));
    inputRef.current?.focus();
  };

  const clearHistory = async () => {
    await fetch(`${API_BASE}/api/v1/chat/history`, { method: "DELETE" });
    setMessages([]);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      mr.start();
      mediaRecRef.current = mr;
      setIsRecording(true);
      setRecordingMs(0);
      setMenuOpen(false);
      timerRef.current = setInterval(() => setRecordingMs((ms) => ms + 100), 100);
    } catch {
      setAudioNotice("Microphone access denied.");
    }
  };

  const cancelRecording = () => {
    const mr = mediaRecRef.current;
    if (!mr) return;
    if (timerRef.current) clearInterval(timerRef.current);
    mr.onstop = () => {
      mr.stream.getTracks().forEach((t) => t.stop());
    };
    mr.stop();
    setIsRecording(false);
  };

  const stopAndSend = () => {
    const mr = mediaRecRef.current;
    if (!mr) return;
    if (timerRef.current) clearInterval(timerRef.current);
    mr.onstop = async () => {
      const blob = new Blob(chunksRef.current, {
        type: mr.mimeType || "audio/webm",
      });
      mr.stream.getTracks().forEach((t) => t.stop());
      setIsRecording(false);
      setMenuOpen(false);
      await sendAudio(blob, mr.mimeType);
    };
    mr.stop();
  };

  const sendAudio = async (blob: Blob, mimeType: string) => {
    setLoading(true);
    setStreamDraft("");
    setStreamNotice(null);
    setAudioNotice(null);
    streamBufferRef.current = "";

    const ext = mimeType.includes("ogg") ? "ogg" : mimeType.includes("mp4") ? "mp4" : "webm";
    const form = new FormData();
    form.append("audio", blob, `recording.${ext}`);
    form.append("backend_name", "groq");

    setMessages((prev) => [
      ...prev,
      { id: makeId(), role: "user", content: "🎤 (audio)" },
      { id: makeId(), role: "assistant", content: "" },
    ]);

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/audio`, {
        method: "POST",
        body: form,
      });
      if (!response.body) throw new Error("No body");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      const flushStream = () => {
        setStreamDraft(streamBufferRef.current);
        streamFlushRef.current = null;
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            const { event, data } = payload;
            if (event === "transcribed") {
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 2] = {
                  ...msgs[msgs.length - 2],
                  role: "user",
                  content: `🎤 ${data.text}`,
                };
                return msgs;
              });
            }
            if (event === "emotion") {
              setMessages((prev) => {
                const msgs = [...prev];
                const userIdx = msgs.length - 2;
                if (userIdx >= 0 && msgs[userIdx].role === "user") {
                  msgs[userIdx] = {
                    ...msgs[userIdx],
                    emotion: { label: data.emotion, score: data.score },
                  };
                }
                return msgs;
              });
            }
            if (event === "token") {
              streamBufferRef.current += data.text;
              if (!streamFlushRef.current) {
                streamFlushRef.current = setTimeout(flushStream, 80);
              }
            }
            if (event === "error") {
              setAudioNotice(data.message || "Audio send failed.");
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = {
                  ...msgs[msgs.length - 1],
                  role: "assistant",
                  content: "⚠ " + (data.message || "Audio send failed."),
                  tag: "error",
                };
                return msgs;
              });
            }
            if (event === "done") {
              if (streamFlushRef.current) {
                clearTimeout(streamFlushRef.current);
                streamFlushRef.current = null;
              }
              if (streamBufferRef.current) {
                const finalText = streamBufferRef.current;
                streamBufferRef.current = "";
                setMessages((prev) => {
                  const msgs = [...prev];
                  msgs[msgs.length - 1] = {
                    ...msgs[msgs.length - 1],
                    content: finalText,
                  };
                  return msgs;
                });
                setStreamDraft("");
              }
            }
          } catch {
            // skip
          }
        }
      }
    } catch {
      setAudioNotice("Audio send failed. Please try again.");
      setMessages((prev) => {
        const msgs = [...prev];
        msgs[msgs.length - 1] = {
          ...msgs[msgs.length - 1],
          role: "assistant",
          content: "⚠ Audio send failed.",
          tag: "error",
        };
        return msgs;
      });
    } finally {
      if (streamFlushRef.current) {
        clearTimeout(streamFlushRef.current);
        streamFlushRef.current = null;
      }
      if (streamBufferRef.current) {
        const finalText = streamBufferRef.current;
        streamBufferRef.current = "";
        setMessages((prev) => {
          const msgs = [...prev];
          msgs[msgs.length - 1] = {
            ...msgs[msgs.length - 1],
            content: finalText,
          };
          return msgs;
        });
        setStreamDraft("");
      }
      setLoading(false);
    }
  };

  const fmtTime = (ms: number) => {
    const s = Math.floor(ms / 1000);
    return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  };

  return (
    <div className={`flex flex-col gap-6 lg:flex-row lg:items-start ${bodyFont.className} ${displayFont.variable} ${bodyFont.variable}`}>
      <section className="flex flex-1 min-h-[calc(100vh-14rem)] lg:min-h-[75vh] flex-col rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 sm:p-8 shadow-[0_8px_32px_rgba(15,23,42,0.03)]">
        <ChatHeader onClear={clearHistory} />

        <div className="my-6 h-px w-full bg-[color:var(--border-soft)] opacity-60" />

        {messageViews.length === 0 && (
          <div className="rounded-xl border border-dashed border-[color:var(--border-soft)] bg-[color:var(--panel)] px-6 py-8 text-center text-sm text-[color:var(--muted-foreground)]">
            <p>Start a conversation with your health companion.</p>
            <p className="mt-2 text-xs opacity-60">Log meals, ask about nutrition, or check your adherence status.</p>
          </div>
        )}

        <MessageList
          messages={messageViews}
          streamDraft={streamDraft}
          loading={loading}
          streamNotice={streamNotice}
          audioNotice={audioNotice}
          onMealAction={handleMealProposal}
          proposalLoadingId={proposalLoadingId}
          bottomRef={bottomRef}
        />

        {menuOpen && <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />}

        <StickyComposer
          input={input}
          inputRef={inputRef}
          onInputChange={setInput}
          onKeyDown={handleKeyDown}
          onSend={handleSend}
          loading={loading}
          onPrependTrack={prependTrack}
          menuOpen={menuOpen}
          onToggleMenu={() => setMenuOpen((prev) => !prev)}
          onStartRecording={startRecording}
          isRecording={isRecording}
          recordingLabel={fmtTime(recordingMs)}
          onStopRecording={stopAndSend}
          onCancelRecording={cancelRecording}
        />
      </section>

      <ChatSidebar />
    </div>
  );
}
