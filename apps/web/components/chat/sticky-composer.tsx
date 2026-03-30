import { type KeyboardEvent, type RefObject } from "react";

type StickyComposerProps = {
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown?: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  inputRef?: RefObject<HTMLTextAreaElement | null>;
  loading: boolean;
  onPrependTrack?: () => void;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onStartRecording: () => void;
  isRecording: boolean;
  recordingLabel?: string;
  onStopRecording?: () => void;
  onCancelRecording?: () => void;
};

export function StickyComposer({
  input,
  onInputChange,
  onSend,
  onKeyDown,
  inputRef,
  loading,
  onPrependTrack,
  menuOpen,
  onToggleMenu,
  onStartRecording,
  isRecording,
  recordingLabel,
  onStopRecording,
  onCancelRecording,
}: StickyComposerProps) {
  return (
    <div className="sticky bottom-0 z-30 -mx-4 -mb-8 mt-4 border-t border-border-soft bg-panel px-4 py-6 sm:-mx-8 sm:px-8">
      <div className="bg-surface border border-border-soft rounded-2xl p-2 shadow-sm focus-within:ring-2 focus-within:ring-accent-teal/20 transition-all">
        {isRecording ? (
          <div className="flex flex-wrap items-center gap-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 px-4 py-3 text-rose-600 dark:text-rose-400 mb-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-sm font-mono font-bold">{recordingLabel ?? "00:00"}</span>
            <span className="text-xs font-semibold flex-1 uppercase tracking-wider">Recording in progress…</span>
            <button
              type="button"
              aria-label="Cancel recording"
              onClick={onCancelRecording}
              className="h-9 w-9 flex items-center justify-center rounded-full text-rose-300 hover:text-rose-500 hover:bg-rose-100 dark:hover:bg-rose-900/50 transition-colors"
            >
              ✕
            </button>
            <button
              type="button"
              aria-label="Stop and send recording"
              onClick={onStopRecording}
              className="h-9 px-4 rounded-full bg-rose-500 text-white text-xs font-bold hover:bg-rose-600 shadow-sm transition-all active:scale-95"
            >
              STOP & SEND
            </button>
          </div>
        ) : null}

        <textarea
          ref={inputRef as any}
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask anything… (Enter to send, Shift+Enter for new line)"
          rows={2}
          aria-label="Message input"
          className="w-full resize-none border-none bg-transparent outline-none text-sm text-foreground placeholder-muted-foreground px-4 py-2 leading-relaxed"
        />

        <div className="flex items-center gap-2 px-2 pb-1">
          <div className="relative z-50">
            <button
              type="button"
              onClick={onToggleMenu}
              aria-label="More options"
              className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-border-soft bg-panel text-muted-foreground hover:text-foreground hover:bg-border-soft transition-all focus-visible:ring-2 focus-visible:ring-accent-teal/40"
            >
              ＋
            </button>
            {menuOpen ? (
              <div className="absolute bottom-full left-0 mb-3 w-56 overflow-hidden rounded-2xl border border-border-soft bg-surface py-2 shadow-xl animate-in slide-in-from-bottom-2 fade-in">
                <button
                  type="button"
                  onClick={onStartRecording}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-medium text-foreground hover:bg-panel transition-colors"
                >
                  <span className="text-base">🎤</span>
                  <span>Record Voice Check‑in</span>
                </button>
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onPrependTrack}
            aria-label="Add [TRACK] prefix"
            className="h-10 px-4 rounded-xl border border-border-soft bg-panel text-xs font-bold text-accent-teal uppercase tracking-wider hover:bg-accent-teal/5 transition-all active:scale-95"
          >
            [TRACK] METRIC
          </button>
          <button
            type="button"
            onClick={onSend}
            disabled={loading || !input.trim()}
            aria-label="Send message"
            className="ml-auto h-10 px-6 rounded-xl bg-accent-teal text-white text-sm font-bold shadow-sm hover:bg-accent-teal/90 disabled:opacity-40 transition-all active:scale-95"
          >
            {loading ? "Thinking…" : "SEND"}
          </button>
        </div>
      </div>
    </div>
  );
}
