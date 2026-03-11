"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend";

type Message = {
  role: "user" | "assistant";
  content: string;
  emotion?: { label: string; score: number };
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

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/chat/history`)
      .then((r) => r.json())
      .then((data) => setMessages(data.messages ?? []))
      .catch(console.error);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const message = input.trim();
    if (!message || loading) return;

    setInput("");
    setLoading(true);
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

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.emotion) {
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
            if (data.text) {
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = {
                  role: "assistant",
                  content: msgs[msgs.length - 1].content + data.text,
                };
                return msgs;
              });
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
        };
        return msgs;
      });
    } finally {
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
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.transcribed) {
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 2] = {
                  ...msgs[msgs.length - 2],
                  role: "user",
                  content: `🎤 ${data.transcribed}`,
                };
                return msgs;
              });
            }
            if (data.emotion) {
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
            if (data.text) {
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = {
                  role: "assistant",
                  content: msgs[msgs.length - 1].content + data.text,
                };
                return msgs;
              });
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
        };
        return msgs;
      });
    } finally {
      setLoading(false);
    }
  };

  const fmtTime = (ms: number) => {
    const s = Math.floor(ms / 1000);
    return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  };

  return (
    <div className="max-w-3xl mx-auto w-full flex flex-col flex-1 px-4 pb-4 h-full">
      <div className="flex items-center justify-between py-4">
        <h1 className="text-2xl font-bold text-gray-800">Chat with SEA-LION</h1>
        <button
          onClick={clearHistory}
          className="text-xs text-gray-400 hover:text-red-500 transition-colors"
        >
          Clear history
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pb-4 min-h-0">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm text-center mt-16">
            Ask about food, medications, or health advice.
            <br />
            Use the{" "}
            <span className="font-mono bg-blue-50 text-blue-600 px-1 rounded">
              [TRACK]
            </span>{" "}
            button to log health metrics for your dashboard.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
                m.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm"
                  : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"
              }`}
            >
              {m.content ||
                (m.role === "assistant" && loading ? (
                  <span className="animate-pulse text-gray-400">▋</span>
                ) : (
                  ""
                ))}{" "}
              {m.emotion && (
                <div className="mt-1.5 text-xs opacity-80 flex items-center gap-1">
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

      <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-3 flex flex-col gap-2 shrink-0">
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
          className="w-full resize-none border-none outline-none text-sm text-gray-800 placeholder-gray-400"
        />
        <div className="flex items-center gap-2">
          <div className="relative z-50">
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="w-8 h-8 rounded-full border border-gray-300 text-gray-500 text-lg flex items-center justify-center hover:bg-gray-100 transition-colors flex-shrink-0"
              title="More options"
            >
              ＋
            </button>
            {menuOpen && (
              <div className="absolute bottom-10 left-0 bg-white border border-gray-200 rounded-2xl shadow-xl py-2 w-52 overflow-hidden">
                <button
                  onClick={() => {
                    setMenuOpen(false);
                    startRecording();
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 transition-colors text-left"
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
            className="text-xs px-3 py-1.5 rounded-full border border-blue-300 text-blue-600 hover:bg-blue-50 transition-colors"
          >
            📍 [TRACK]
          </button>
          <div className="flex-1" />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-5 py-1.5 rounded-full bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
          >
            {loading ? "…" : "Send ➤"}
          </button>
        </div>
      </div>
    </div>
  );
}
