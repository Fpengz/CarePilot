"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend";

type Message = {
  role: "user" | "assistant";
  content: string;
  emotion?: { label: string; score: number };
  tag?: string;
};

const EMOTION_EMOJI: Record<string, string> = {
  happy: "😊",
  sad: "😢",
  angry: "😤",
  frustrated: "😩",
  anxious: "😰",
  neutral: "😐",
  confused: "😕",
  fearful: "😨",
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showAudio, setShowAudio] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingMs, setRecordingMs] = useState(0);
  const [streamDraft, setStreamDraft] = useState("");

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
      .then((data) => setMessages(data.messages ?? []))
      .catch(console.error);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamDraft]);

  useEffect(() => {
    return () => {
      if (streamFlushRef.current) {
        clearTimeout(streamFlushRef.current);
        streamFlushRef.current = null;
      }
    };
  }, []);

  const lastEmotion = useMemo(() => {
    const reversed = [...messages].reverse();
    return reversed.find((m) => m.emotion)?.emotion ?? null;
  }, [messages]);

  const lastUserMessage = useMemo(() => {
    const reversed = [...messages].reverse();
    return reversed.find((m) => m.role === "user")?.content ?? "";
  }, [messages]);

  const handleSend = async () => {
    const message = input.trim();
    if (!message || loading) return;

    setInput("");
    setLoading(true);
    setStreamDraft("");
    streamBufferRef.current = "";
    setMessages((prev) => [
      ...prev,
      { role: "user", content: message },
      { role: "assistant", content: "" },
    ]);

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
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
            if (event === "token") {
              streamBufferRef.current += data.text;
              if (!streamFlushRef.current) {
                streamFlushRef.current = setTimeout(flushStream, 80);
              }
            }
            if (event === "error") {
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = {
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
                    role: "assistant",
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
      setMessages((prev) => {
        const msgs = [...prev];
        msgs[msgs.length - 1] = {
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
            role: "assistant",
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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
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
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.start();
      mediaRecRef.current = mr;
      setIsRecording(true);
      setRecordingMs(0);
      setShowAudio(true);
      timerRef.current = setInterval(() => setRecordingMs((ms) => ms + 100), 100);
    } catch {
      alert("Microphone access denied.");
      setShowAudio(false);
    }
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
      setShowAudio(false);
      setMenuOpen(false);
      await sendAudio(blob, mr.mimeType);
    };
    mr.stop();
  };

  const sendAudio = async (blob: Blob, mimeType: string) => {
    setLoading(true);
    const ext = mimeType.includes("ogg")
      ? "ogg"
      : mimeType.includes("mp4")
        ? "mp4"
        : "webm";
    const form = new FormData();
    form.append("audio", blob, `recording.${ext}`);
    form.append("backend_name", "groq");

    setStreamDraft("");
    streamBufferRef.current = "";
    setMessages((prev) => [
      ...prev,
      { role: "user", content: "🎤 (audio)" },
      { role: "assistant", content: "" },
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
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = {
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
                    role: "assistant",
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
      setMessages((prev) => {
        const msgs = [...prev];
        msgs[msgs.length - 1] = {
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
            role: "assistant",
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
    <div className="page-grid">
      <div className="flex flex-col min-h-[60vh]">
        <div className="flex items-center justify-between py-3">
          <div>
            <div className="section-kicker">Companion chat</div>
            <h1 className="text-3xl font-semibold tracking-[-0.02em]">SEA-LION Conversation</h1>
            <p className="app-muted mt-1 text-sm">Ask about food, medications, or daily care decisions.</p>
          </div>
          <button
            onClick={clearHistory}
            className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted-foreground)] hover:text-red-500 transition-colors"
          >
            Clear history
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 pb-4 min-h-0">
          {messages.length === 0 && (
            <div className="rounded-2xl border border-dashed border-[color:var(--border)] bg-[color:var(--surface)] p-6 text-sm text-[color:var(--muted-foreground)]">
              Start with a health question or log metrics using the{" "}
              <span className="font-mono bg-[color:var(--accent)]/10 text-[color:var(--accent)] px-1 rounded">
                [TRACK]
              </span>{" "}
              action below.
            </div>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
                  m.role === "user"
                    ? "bg-[color:var(--accent)] text-[color:var(--accent-foreground)] rounded-br-sm"
                    : "bg-[color:var(--surface)] border border-[color:var(--border)] text-[color:var(--foreground)] rounded-bl-sm shadow-sm"
                } ${m.tag === "error" ? "border-red-400/40 bg-red-50 text-red-700" : ""}`}
              >
                {m.role === "assistant" ? (
                  m.content || streamDraft ? (
                    <ReactMarkdown className="chat-markdown" rehypePlugins={[rehypeSanitize]}>
                      {m.content || streamDraft}
                    </ReactMarkdown>
                  ) : loading ? (
                    <span className="animate-pulse text-[color:var(--muted-foreground)]">▋</span>
                  ) : (
                    ""
                  )
                ) : (
                  m.content
                )}{" "}
                {m.emotion && (
                  <div className="mt-2 text-xs uppercase tracking-[0.16em] opacity-80 flex items-center gap-2">
                    <span>{EMOTION_EMOJI[m.emotion.label] ?? "🫥"}</span>
                    <span className="capitalize">{m.emotion.label}</span>
                    <span className="opacity-60">
                      ({Math.round(m.emotion.score * 100)}%)
                    </span>
                  </div>
                )}{" "}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {menuOpen && (
          <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
        )}

        <div className="bg-[color:var(--panel)] border border-[color:var(--border)] rounded-2xl shadow-sm p-3 flex flex-col gap-2 shrink-0">
          {showAudio && isRecording && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse inline-block" />
              <span className="text-sm text-red-600 font-mono">{fmtTime(recordingMs)}</span>
              <span className="text-xs text-red-500 flex-1">Recording…</span>
              <button
                onClick={() => {
                  const mr = mediaRecRef.current;
                  if (mr) {
                    if (timerRef.current) clearInterval(timerRef.current);
                    mr.onstop = () => {
                      mr.stream.getTracks().forEach((t) => t.stop());
                    };
                    mr.stop();
                  }
                  setIsRecording(false);
                  setShowAudio(false);
                }}
                className="text-xs text-gray-400 hover:text-gray-600 px-2"
              >
                ✕
              </button>
              <button
                onClick={stopAndSend}
                className="text-xs px-3 py-1.5 rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors"
              >
                ⏹ Stop &amp; Send
              </button>
            </div>
          )}

          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything… (Enter to send, Shift+Enter for new line)"
            rows={2}
            className="w-full resize-none border-none bg-transparent outline-none text-sm text-[color:var(--foreground)] placeholder-[color:var(--muted-foreground)]"
          />
          <div className="flex items-center gap-2">
            <div className="relative z-50">
              <button
                onClick={() => setMenuOpen((v) => !v)}
                className="w-8 h-8 rounded-full border border-[color:var(--border)] text-[color:var(--muted-foreground)] text-lg flex items-center justify-center hover:bg-[color:var(--accent)]/10 transition-colors flex-shrink-0"
                title="More options"
              >
                ＋
              </button>
              {menuOpen && (
                <div className="absolute bottom-10 left-0 bg-[color:var(--panel)] border border-[color:var(--border)] rounded-2xl shadow-xl py-2 w-52 overflow-hidden">
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      startRecording();
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-[color:var(--foreground)] hover:bg-black/5 transition-colors text-left"
                  >
                    <span className="text-base">🎤</span>
                    <span>Record Audio</span>
                  </button>
                </div>
              )}
            </div>
            <button
              onClick={prependTrack}
              title="Prefix your message with [TRACK] to log a health metric"
              className="text-xs px-3 py-1.5 rounded-full border border-[color:var(--accent)]/40 text-[color:var(--accent)] hover:bg-[color:var(--accent)]/10 transition-colors"
            >
              Add [TRACK]
            </button>
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="ml-auto text-sm font-medium px-4 py-2 rounded-full bg-[color:var(--accent)] text-[color:var(--accent-foreground)] hover:opacity-90 disabled:opacity-40 transition-colors"
            >
              {loading ? "Thinking…" : "Send"}
            </button>
          </div>
        </div>
      </div>

      <aside className="space-y-4">
        <div className="app-panel p-4">
          <div className="section-kicker">Session signal</div>
          <div className="mt-2 text-sm text-[color:var(--foreground)]">
            {lastEmotion ? (
              <div className="flex items-center gap-2">
                <span className="text-base">{EMOTION_EMOJI[lastEmotion.label] ?? "🫥"}</span>
                <span className="capitalize">{lastEmotion.label}</span>
                <span className="text-xs text-[color:var(--muted-foreground)]">
                  {Math.round(lastEmotion.score * 100)}%
                </span>
              </div>
            ) : (
              <p className="app-muted">No emotion signal captured yet.</p>
            )}
          </div>
        </div>
        <div className="app-panel p-4">
          <div className="section-kicker">Last user intent</div>
          <p className="mt-2 text-sm text-[color:var(--foreground)]">
            {lastUserMessage || "Awaiting the first question."}
          </p>
        </div>
      </aside>
    </div>
  );
}
