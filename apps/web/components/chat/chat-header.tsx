import { Button } from "@/components/ui/button";

export function ChatHeader({ onClear }: { onClear: () => void }) {
  return (
    <div className="flex items-center justify-end">
      <Button variant="secondary" size="sm" onClick={onClear}>
        Clear history
      </Button>
    </div>
  );
}
