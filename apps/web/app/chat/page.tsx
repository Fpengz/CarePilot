"use client";

import { Fraunces, Source_Sans_3 } from "next/font/google";
import { ChatSidebar } from "./components/chat-sidebar";
import { ChatHeader } from "@/components/chat/chat-header";
import { MessageList } from "@/components/chat/message-list";
import { StickyComposer } from "@/components/chat/sticky-composer";
import { useChat } from "./hooks/use-chat";

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

export default function ChatPage() {
  const {
    messageViews,
    input,
    setInput,
    loading,
    menuOpen,
    setMenuOpen,
    isRecording,
    recordingMs,
    streamDraft,
    proposalLoadingId,
    streamNotice,
    audioNotice,
    bottomRef,
    inputRef,
    handleSend,
    handleMealProposal,
    handleKeyDown,
    prependTrack,
    startRecording,
    cancelRecording,
    stopAndSend,
    clearHistory,
  } = useChat();

  const fmtTime = (ms: number) => {
    const s = Math.floor(ms / 1000);
    return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  };

  return (
    <main className={`flex flex-col gap-8 lg:flex-row lg:items-start relative isolate min-h-[calc(100vh-6rem)] ${bodyFont.className} ${displayFont.variable} ${bodyFont.variable}`}>
      <div className="dashboard-grounding" aria-hidden="true" />
      
      {/* Main Conversation Workspace */}
      <section className="flex flex-1 flex-col bg-surface border border-border-soft rounded-3xl shadow-sm overflow-hidden min-h-[calc(100vh-10rem)] lg:min-h-[80vh]">
        <header className="bg-panel px-6 py-4 border-b border-border-soft flex items-center justify-between">
          <ChatHeader onClear={clearHistory} />
        </header>

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

        <footer className="bg-panel border-t border-border-soft p-4 sm:p-6">
          <div className="max-w-4xl mx-auto relative">
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
        </footer>
      </section>

      {/* Right Rail: Health Context */}
      <aside className="w-full lg:w-80 shrink-0">
        <ChatSidebar />
      </aside>
    </main>
  );
}
