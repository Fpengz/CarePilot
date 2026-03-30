"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
  const queryClient = useQueryClient();
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
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

  // Fetch chat history
  const { data: historyData } = useQuery({
    queryKey: ["chat", "history"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/v1/chat/history`);
      if (!response.ok) throw new Error("Failed to fetch history");
      return response.json();
    },
  });

  // Consolidate messages: history + local session messages (rerender-derived-state-no-effect)
  const messages = useMemo(() => {
    const history = (historyData?.messages || []).map((m: any, idx: number) => normalizeMessage(m, idx));
    return localMessages.length > 0 ? localMessages : history;
  }, [historyData, localMessages]);

  // Mutation for clearing history
  const clearHistoryMutation = useMutation({
    mutationFn: async () => {
      await fetch(`${API_BASE}/api/v1/chat/history`, { method: "DELETE" });
    },
    onSuccess: () => {
      setLocalMessages([]);
      queryClient.invalidateQueries({ queryKey: ["chat", "history"] });
    },
  });

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

  const messageViews = useMemo(() => messages.map((m: Message) => deriveMessageView(m)), [messages]);

  const handleSend = useCallback(async () => {
    const messageText = input.trim();
    if (!messageText || loading) return;

    setInput("");
    setLoading(true);
    setStreamDraft("");
    setStreamNotice(null);
    setAudioNotice(null);
    streamBufferRef.current = "";
    
    const userMessageId = makeId();
    const assistantMessageId = makeId();
    
    setLocalMessages((prev) => {
      const base = prev.length > 0 ? prev : (historyData?.messages || []).map((m: any, idx: number) => normalizeMessage(m, idx));
      return [
        ...base,
        { id: userMessageId, role: "user", content: messageText },
        { id: assistantMessageId, role: "assistant", content: "" },
      ];
    });

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
          
          let payload;
          try {
            payload = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          const { event, data } = payload;
          
          if (event === "emotion") {
            setLocalMessages((prev) => {
              const msgs = [...prev];
              const userIdx = msgs.findIndex(m => m.id === userMessageId);
              if (userIdx >= 0) {
                msgs[userIdx] = { ...msgs[userIdx], emotion: { label: data.emotion, score: data.score } };
              }
              return msgs;
            });
          } else if (event === "meal_proposed") {
            setLocalMessages((prev) => {
              const msgs = [...prev];
              const idx = msgs.findIndex(m => m.id === assistantMessageId);
              if (idx >= 0) {
                msgs[idx] = { ...msgs[idx], mealProposal: { proposalId: data.proposal_id, mealText: data.meal_text } };
              }
              return msgs;
            });
          } else if (event === "token") {
            streamBufferRef.current += data.text;
            if (!streamFlushRef.current) {
              streamFlushRef.current = setTimeout(flushStream, 80);
            }
          } else if (event === "error") {
            setStreamNotice(data.message || "Streaming response interrupted.");
            setLocalMessages((prev) => {
              const msgs = [...prev];
              const idx = msgs.findIndex(m => m.id === assistantMessageId);
              if (idx >= 0) {
                msgs[idx] = { ...msgs[idx], content: "⚠ " + (data.message || "Request failed."), tag: "error" };
              }
              return msgs;
            });
          } else if (event === "done") {
            if (streamFlushRef.current) {
              clearTimeout(streamFlushRef.current);
              streamFlushRef.current = null;
            }
            if (streamBufferRef.current) {
              const finalText = streamBufferRef.current;
              streamBufferRef.current = "";
              setLocalMessages((prev) => {
                const msgs = [...prev];
                const idx = msgs.findIndex(m => m.id === assistantMessageId);
                if (idx >= 0) {
                  const last = msgs[idx];
                  msgs[idx] = { ...msgs[idx], content: last.content + finalText };
                }
                return msgs;
              });
              setStreamDraft("");
            }
            queryClient.invalidateQueries({ queryKey: ["chat", "history"] });
          }
        }
      }
    } catch {
      setStreamNotice("Unable to reach the server. Check backend status.");
      setLocalMessages((prev) => {
        const msgs = [...prev];
        const idx = msgs.findIndex(m => m.id === assistantMessageId);
        if (idx >= 0) {
          msgs[idx] = { ...msgs[idx], content: "⚠ Could not reach the server.", tag: "error" };
        }
        return msgs;
      });
    } finally {
      if (streamFlushRef.current) {
        clearTimeout(streamFlushRef.current);
        streamFlushRef.current = null;
      }
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [input, loading, historyData, queryClient]);

  const handleMealProposal = useCallback(async (proposalId: string, action: "confirm" | "skip") => {
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
      setLocalMessages((prev) => {
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
      queryClient.invalidateQueries({ queryKey: ["chat", "history"] });
    } catch {
      setLocalMessages((prev) => {
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
  }, [proposalLoadingId, queryClient]);

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

  const sendAudio = useCallback(async (blob: Blob, mimeType: string) => {
    setLoading(true);
    setStreamDraft("");
    setStreamNotice(null);
    setAudioNotice(null);
    streamBufferRef.current = "";

    const ext = mimeType.includes("ogg") ? "ogg" : mimeType.includes("mp4") ? "mp4" : "webm";
    const form = new FormData();
    form.append("audio", blob, `recording.${ext}`);
    form.append("backend_name", "groq");

    const userMessageId = makeId();
    const assistantMessageId = makeId();

    setLocalMessages((prev) => {
      const base = prev.length > 0 ? prev : (historyData?.messages || []).map((m: any, idx: number) => normalizeMessage(m, idx));
      return [
        ...base,
        { id: userMessageId, role: "user", content: "🎤 (audio)" },
        { id: assistantMessageId, role: "assistant", content: "" },
      ];
    });

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
              setLocalMessages((prev) => {
                const msgs = [...prev];
                const idx = msgs.findIndex(m => m.id === userMessageId);
                if (idx >= 0) {
                  msgs[idx] = { ...msgs[idx], content: `🎤 ${data.text}` };
                }
                return msgs;
              });
            }
            if (event === "emotion") {
              setLocalMessages((prev) => {
                const msgs = [...prev];
                const userIdx = msgs.findIndex(m => m.id === userMessageId);
                if (userIdx >= 0) {
                  msgs[userIdx] = {
                    ...msgs[userIdx],
                    emotion: { label: data.emotion, score: data.score },
                  };
                }
                return msgs;
              });
            }
            if (event === "meal_proposed") {
              setLocalMessages((prev) => {
                const msgs = [...prev];
                const idx = msgs.findIndex(m => m.id === assistantMessageId);
                if (idx >= 0) {
                  msgs[idx] = {
                    ...msgs[idx],
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
              setAudioNotice(data.message || "Audio send failed.");
              setLocalMessages((prev) => {
                const msgs = [...prev];
                const idx = msgs.findIndex(m => m.id === assistantMessageId);
                if (idx >= 0) {
                  msgs[idx] = {
                    ...msgs[idx],
                    content: "⚠ " + (data.message || "Audio send failed."),
                    tag: "error",
                  };
                }
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
                setLocalMessages((prev) => {
                  const msgs = [...prev];
                  const idx = msgs.findIndex(m => m.id === assistantMessageId);
                  if (idx >= 0) {
                    const last = msgs[idx];
                    msgs[idx] = { ...msgs[idx], content: last.content + finalText };
                  }
                  return msgs;
                });
                setStreamDraft("");
              }
              queryClient.invalidateQueries({ queryKey: ["chat", "history"] });
            }
          } catch {
            // skip
          }
        }
      }
    } catch {
      setAudioNotice("Audio send failed. Please try again.");
      setLocalMessages((prev) => {
        const msgs = [...prev];
        const idx = msgs.findIndex(m => m.id === assistantMessageId);
        if (idx >= 0) {
          msgs[idx] = {
            ...msgs[idx],
            content: "⚠ Audio send failed.",
            tag: "error",
          };
        }
        return msgs;
      });
    } finally {
      if (streamFlushRef.current) {
        clearTimeout(streamFlushRef.current);
        streamFlushRef.current = null;
      }
      setLoading(false);
    }
  }, [historyData, queryClient]);

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

  const fmtTime = (ms: number) => {
    const s = Math.floor(ms / 1000);
    return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  };

  return (
    <div className={`flex flex-col gap-8 lg:flex-row lg:items-start relative isolate min-h-[calc(100vh-6rem)] ${bodyFont.className} ${displayFont.variable} ${bodyFont.variable}`}>
      <div className="dashboard-grounding" />
      
      {/* Main Conversation Workspace */}
      <section className="flex flex-1 flex-col bg-surface border border-border-soft rounded-3xl shadow-sm overflow-hidden min-h-[calc(100vh-10rem)] lg:min-h-[80vh]">
        <div className="bg-panel px-6 py-4 border-b border-border-soft flex items-center justify-between">
          <ChatHeader onClear={() => clearHistoryMutation.mutate()} />
        </div>

        <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-8">
          {messageViews.length === 0 && (
            <div className="max-w-2xl mx-auto rounded-2xl border border-dashed border-border-soft bg-panel/50 px-8 py-16 text-center">
              <p className="text-lg font-semibold text-foreground">Health Companion Workspace</p>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                Log meals, ask about nutrition, or check your adherence status. 
                Your conversation history is securely persisted for clinical context.
              </p>
            </div>
          )}

          <div className="max-w-4xl mx-auto">
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
          </div>
        </div>

        <div className="bg-panel border-t border-border-soft p-4 sm:p-6">
          <div className="max-w-4xl mx-auto relative">
            {menuOpen && <div className="fixed inset-0 z-20" onClick={() => setMenuOpen(false)} />}
            
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
          </div>
        </div>
      </section>

      {/* Right Rail: Health Context */}
      <div className="w-full lg:w-80 shrink-0 space-y-6">
        <ChatSidebar />
      </div>
    </div>
  );
}
