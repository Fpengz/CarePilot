"use client";

import { useState } from "react";
import { Upload, Keyboard, FileText, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AsyncLabel } from "@/components/app/async-label";
import { cn } from "@/lib/utils";

interface MedicationIntakeWizardProps {
  onTextIntake: (text: string) => void;
  onFileUpload: (file: File) => void;
  busy?: boolean;
}

export function MedicationIntakeWizard({ onTextIntake, onFileUpload, busy }: MedicationIntakeWizardProps) {
  const [mode, setMode] = useState<"choice" | "text" | "upload">("choice");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);

  return (
    <div className="clinical-card space-y-8">
      <div className="space-y-1">
        <h3 className="clinical-subtitle">Intake Assistant</h3>
        <p className="clinical-body">
          Add new medications to your care plan by pasting a prescription or uploading a clinical document.
        </p>
      </div>

      {mode === "choice" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <button 
            onClick={() => setMode("text")}
            className="flex flex-col items-center justify-center gap-4 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-8 transition-all hover:border-[color:var(--accent)] hover:bg-[color:var(--accent)]/[0.02] hover:shadow-sm"
          >
            <div className="rounded-full bg-[color:var(--accent)]/10 p-3 text-[color:var(--accent)]">
              <Keyboard className="h-6 w-6" />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold tracking-tight">Paste Text</div>
              <p className="mt-1 text-xs text-[color:var(--muted-foreground)] opacity-60">Paste from clipboard</p>
            </div>
          </button>
          
          <button 
            onClick={() => setMode("upload")}
            className="flex flex-col items-center justify-center gap-4 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-8 transition-all hover:border-[color:var(--accent)] hover:bg-[color:var(--accent)]/[0.02] hover:shadow-sm"
          >
            <div className="rounded-full bg-[color:var(--accent)]/10 p-3 text-[color:var(--accent)]">
              <Upload className="h-6 w-6" />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold tracking-tight">Upload Image/PDF</div>
              <p className="mt-1 text-xs text-[color:var(--muted-foreground)] opacity-60">Scan prescription</p>
            </div>
          </button>
        </div>
      )}

      {mode === "text" && (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
          <div className="space-y-2">
            <Label htmlFor="intake-text">Instructions</Label>
            <Textarea
              id="intake-text"
              placeholder="Take Metformin 500mg twice daily before meals..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
              className="rounded-xl"
            />
          </div>
          <div className="flex gap-2">
            <Button 
              className="flex-1 rounded-xl h-11" 
              onClick={() => onTextIntake(text)} 
              disabled={busy || !text.trim()}
            >
              <AsyncLabel active={!!busy} loading="Parsing" idle="Analyze Instructions" />
            </Button>
            <Button variant="ghost" className="rounded-xl h-11" onClick={() => setMode("choice")}>Cancel</Button>
          </div>
        </div>
      )}

      {mode === "upload" && (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
          <div className="space-y-2">
            <Label htmlFor="intake-file">Prescription Document</Label>
            <Input
              id="intake-file"
              type="file"
              accept=".pdf,.txt,image/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="rounded-xl h-11 py-2"
            />
          </div>
          <div className="flex gap-2">
            <Button 
              className="flex-1 rounded-xl h-11" 
              onClick={() => file && onFileUpload(file)} 
              disabled={busy || !file}
            >
              <AsyncLabel active={!!busy} loading="Uploading" idle="Analyze Document" />
            </Button>
            <Button variant="ghost" className="rounded-xl h-11" onClick={() => setMode("choice")}>Cancel</Button>
          </div>
        </div>
      )}
    </div>
  );
}
