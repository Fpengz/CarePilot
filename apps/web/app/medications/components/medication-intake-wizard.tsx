"use client";

import { useState } from "react";
import { Upload, Keyboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AsyncLabel } from "@/components/app/async-label";

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
<<<<<<< Updated upstream
    <div className="space-y-10">
      <div className="space-y-1.5 px-1">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-teal">Intake Assistant</h3>
        <p className="text-[13px] text-muted-foreground leading-relaxed max-w-xl">
          Add new medications to your care plan by pasting instructions or uploading a clinical document.
=======
    <div className="bg-panel border border-border-soft rounded-3xl p-8 shadow-sm space-y-8">
      <div className="space-y-1">
        <h3 className="text-xl font-semibold tracking-tight text-foreground">Intake Assistant</h3>
        <p className="text-sm text-muted-foreground font-medium">
          Add new medications to your care plan by pasting a prescription or uploading a clinical document.
>>>>>>> Stashed changes
        </p>
      </div>

      {mode === "choice" && (
        <div className="grid gap-6 sm:grid-cols-2">
          <button 
            onClick={() => setMode("text")}
<<<<<<< Updated upstream
            className="group flex flex-col items-center justify-center gap-5 rounded-2xl border border-border-soft bg-panel p-10 transition-all hover:border-accent-teal/30 hover:bg-surface hover:shadow-sm"
          >
            <div className="rounded-xl bg-accent-teal/10 p-3.5 text-accent-teal group-hover:scale-110 transition-transform">
              <Keyboard className="h-6 w-6" aria-hidden="true" />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold tracking-tight text-foreground uppercase tracking-widest">Paste Text</div>
              <p className="mt-1.5 text-[11px] font-medium text-muted-foreground opacity-60">Paste from clipboard</p>
=======
            className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-border-soft bg-surface p-8 transition-all hover:border-accent-teal/30 hover:bg-accent-teal/5 shadow-sm group"
          >
            <div className="rounded-2xl bg-panel border border-border-soft p-4 text-muted-foreground group-hover:text-accent-teal group-hover:bg-surface transition-all">
              <Keyboard className="h-8 w-8" />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold tracking-tight text-foreground">Paste Text</div>
              <p className="mt-1 text-xs text-muted-foreground font-medium opacity-60">Paste from clipboard</p>
>>>>>>> Stashed changes
            </div>
          </button>
          
          <button 
            onClick={() => setMode("upload")}
<<<<<<< Updated upstream
            className="group flex flex-col items-center justify-center gap-5 rounded-2xl border border-border-soft bg-panel p-10 transition-all hover:border-accent-teal/30 hover:bg-surface hover:shadow-sm"
          >
            <div className="rounded-xl bg-accent-teal/10 p-3.5 text-accent-teal group-hover:scale-110 transition-transform">
              <Upload className="h-6 w-6" aria-hidden="true" />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold tracking-tight text-foreground uppercase tracking-widest">Upload Document</div>
              <p className="mt-1.5 text-[11px] font-medium text-muted-foreground opacity-60">PDF, JPEG, or PNG</p>
=======
            className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-border-soft bg-surface p-8 transition-all hover:border-accent-teal/30 hover:bg-accent-teal/5 shadow-sm group"
          >
            <div className="rounded-2xl bg-panel border border-border-soft p-4 text-muted-foreground group-hover:text-accent-teal group-hover:bg-surface transition-all">
              <Upload className="h-8 w-8" />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold tracking-tight text-foreground">Upload Image/PDF</div>
              <p className="mt-1 text-xs text-muted-foreground font-medium opacity-60">Scan prescription</p>
>>>>>>> Stashed changes
            </div>
          </button>
        </div>
      )}

      {mode === "text" && (
        <div className="space-y-6 animate-in fade-in slide-in-from-top-2">
          <div className="space-y-3">
<<<<<<< Updated upstream
            <Label htmlFor="intake-text" className="text-xs font-bold uppercase tracking-widest text-muted-foreground px-1">Clinical Instructions</Label>
=======
            <Label htmlFor="intake-text" className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground ml-1">Instructions</Label>
>>>>>>> Stashed changes
            <Textarea
              id="intake-text"
              placeholder="e.g., Take Metformin 500mg twice daily before meals..."
              value={text}
              onChange={(e) => setText(e.target.value)}
<<<<<<< Updated upstream
              rows={5}
              className="rounded-xl border-border-soft bg-panel focus:bg-surface transition-colors leading-relaxed"
=======
              rows={4}
              className="rounded-2xl bg-surface border-border-soft shadow-sm p-4 text-sm leading-relaxed"
>>>>>>> Stashed changes
            />
          </div>
          <div className="flex gap-3">
            <Button 
<<<<<<< Updated upstream
              className="flex-1 rounded-xl h-12 font-bold shadow-sm" 
=======
              className="flex-1 rounded-xl h-12 font-bold bg-accent-teal hover:bg-accent-teal/90 text-white shadow-lg shadow-accent-teal/20" 
>>>>>>> Stashed changes
              onClick={() => onTextIntake(text)} 
              disabled={busy || !text.trim()}
            >
              <AsyncLabel active={!!busy} loading="Analyzing" idle="Parse Instructions" />
            </Button>
            <Button variant="secondary" className="rounded-xl h-12 px-8 font-semibold" onClick={() => setMode("choice")}>Cancel</Button>
          </div>
        </div>
      )}

      {mode === "upload" && (
        <div className="space-y-6 animate-in fade-in slide-in-from-top-2">
          <div className="space-y-3">
<<<<<<< Updated upstream
            <Label htmlFor="intake-file" className="text-xs font-bold uppercase tracking-widest text-muted-foreground px-1">Prescription Document</Label>
=======
            <Label htmlFor="intake-file" className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground ml-1">Prescription Document</Label>
>>>>>>> Stashed changes
            <Input
              id="intake-file"
              type="file"
              accept=".pdf,.txt,image/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
<<<<<<< Updated upstream
              className="rounded-xl h-12 py-3 border-border-soft bg-panel file:mr-4 file:py-0 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-accent-teal/10 file:text-accent-teal hover:file:bg-accent-teal/20"
=======
              className="rounded-2xl h-12 py-2 bg-surface border-border-soft shadow-sm px-4"
>>>>>>> Stashed changes
            />
          </div>
          <div className="flex gap-3">
            <Button 
<<<<<<< Updated upstream
              className="flex-1 rounded-xl h-12 font-bold shadow-sm" 
=======
              className="flex-1 rounded-xl h-12 font-bold bg-accent-teal hover:bg-accent-teal/90 text-white shadow-lg shadow-accent-teal/20" 
>>>>>>> Stashed changes
              onClick={() => file && onFileUpload(file)} 
              disabled={busy || !file}
            >
              <AsyncLabel active={!!busy} loading="Uploading" idle="Analyze Document" />
            </Button>
            <Button variant="secondary" className="rounded-xl h-12 px-8 font-semibold" onClick={() => setMode("choice")}>Cancel</Button>
          </div>
        </div>
      )}
    </div>
  );
}
