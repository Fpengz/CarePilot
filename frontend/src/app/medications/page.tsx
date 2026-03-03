"use client";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Med = {
  id: number;
  medicine: string;
  dose_notes: string;
  schedule: string;
  added: string;
};
type ParsedEntry = {
  medicine_name: string;
  dose_notes: string;
  timing_labels: string[];
};

const TIMING_LABELS = [
  "Before Breakfast",
  "After Breakfast",
  "Before Lunch",
  "After Lunch",
  "Before Dinner",
  "After Dinner",
];

export default function MedicationsPage() {
  const [meds, setMeds] = useState<Med[]>([]);
  const [status, setStatus] = useState("");

  // Manual add form
  const [name, setName] = useState("");
  const [dose, setDose] = useState("");
  const [timing, setTiming] = useState<string[]>([]);

  // Prescription parse
  const [rxText, setRxText] = useState("");
  const [preview, setPreview] = useState<ParsedEntry[]>([]);
  const [rxStatus, setRxStatus] = useState("");

  // Delete
  const [deleteId, setDeleteId] = useState("");

  const loadMeds = () =>
    fetch(`${API_BASE}/api/medications`)
      .then((r) => r.json())
      .then((d) => setMeds(d.medications ?? []))
      .catch(console.error);

  useEffect(() => {
    loadMeds();
  }, []);

  const toggleTiming = (label: string) =>
    setTiming((prev) =>
      prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label],
    );

  const handleAdd = async () => {
    if (!name.trim()) {
      setStatus("⚠ Medicine name is required.");
      return;
    }
    const res = await fetch(`${API_BASE}/api/medications/manual`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, dose_notes: dose, timing_labels: timing }),
    });
    const data = await res.json();
    if (res.ok) {
      setMeds(data.medications);
      setName("");
      setDose("");
      setTiming([]);
      setStatus(`✅ Added '${name}'.`);
    } else {
      setStatus(`❌ ${data.detail}`);
    }
  };

  const handleDelete = async () => {
    const id = parseInt(deleteId);
    if (isNaN(id)) {
      setStatus("⚠ Enter a valid numeric ID.");
      return;
    }
    const res = await fetch(`${API_BASE}/api/medications/${id}`, {
      method: "DELETE",
    });
    const data = await res.json();
    if (res.ok) {
      setMeds(data.medications);
      setDeleteId("");
      setStatus(`✅ Deleted ID ${id}.`);
    } else {
      setStatus(`❌ ${data.detail}`);
    }
  };

  const handleParsePreview = async () => {
    if (!rxText.trim()) {
      setRxStatus("⚠ Paste some prescription text first.");
      return;
    }
    const res = await fetch(`${API_BASE}/api/medications/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: rxText }),
    });
    const data = await res.json();
    if (res.ok) {
      setPreview(data.entries);
      setRxStatus(
        `✅ Found ${data.count} medication(s). Review then click Save All.`,
      );
    } else {
      setRxStatus(`❌ ${data.detail}`);
    }
  };

  const handleSaveAll = async () => {
    if (!rxText.trim()) return;
    const res = await fetch(`${API_BASE}/api/medications/save-parsed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: rxText }),
    });
    const data = await res.json();
    if (res.ok) {
      setMeds(data.medications);
      setPreview([]);
      setRxText("");
      setRxStatus(`✅ Saved ${data.saved} medication(s).`);
    } else {
      setRxStatus(`❌ ${data.detail}`);
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full px-4 py-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-800">
        💊 My Medication Schedule
      </h1>

      {/* ── Parse prescription ── */}
      <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-700">
          📋 Parse from Prescription
        </h2>
        <textarea
          value={rxText}
          onChange={(e) => setRxText(e.target.value)}
          rows={5}
          placeholder={
            "Paste prescription text here, e.g.\nMetformin 500mg twice daily after meals."
          }
          className="w-full border border-gray-200 rounded-xl p-3 text-sm resize-none outline-none focus:ring-2 focus:ring-blue-300"
        />
        <div className="flex gap-2">
          <button onClick={handleParsePreview} className="btn-secondary">
            🔍 Preview
          </button>
          <button onClick={handleSaveAll} className="btn-primary">
            💾 Parse & Save All
          </button>
        </div>
        {rxStatus && <p className="text-sm text-gray-600">{rxStatus}</p>}
        {preview.length > 0 && (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 text-left">
                <th className="p-2 border border-gray-200">Medicine</th>
                <th className="p-2 border border-gray-200">Dose</th>
                <th className="p-2 border border-gray-200">Schedule</th>
              </tr>
            </thead>
            <tbody>
              {preview.map((e, i) => (
                <tr key={i} className="even:bg-gray-50">
                  <td className="p-2 border border-gray-200">
                    {e.medicine_name}
                  </td>
                  <td className="p-2 border border-gray-200">
                    {e.dose_notes || "—"}
                  </td>
                  <td className="p-2 border border-gray-200">
                    {e.timing_labels.join(", ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* ── Manual add ── */}
      <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-700">✏️ Add Manually</h2>
        <div className="grid grid-cols-2 gap-3">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Medicine name (e.g. Metformin 500mg)"
            className="input-field"
          />
          <input
            value={dose}
            onChange={(e) => setDose(e.target.value)}
            placeholder="Dose / notes (optional)"
            className="input-field"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {TIMING_LABELS.map((label) => (
            <button
              key={label}
              onClick={() => toggleTiming(label)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                timing.includes(label)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button onClick={handleAdd} className="btn-primary">
          ➕ Add Medication
        </button>
        {status && <p className="text-sm text-gray-600">{status}</p>}
      </section>

      {/* ── Current schedule ── */}
      <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-700">
          📅 Current Schedule
        </h2>
        {meds.length === 0 ? (
          <p className="text-sm text-gray-400">No medications added yet.</p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 text-left">
                {["ID", "Medicine", "Dose / Notes", "Schedule", "Added"].map(
                  (h) => (
                    <th
                      key={h}
                      className="p-2 border border-gray-200 font-medium"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {meds.map((m) => (
                <tr key={m.id} className="even:bg-gray-50">
                  <td className="p-2 border border-gray-200 text-gray-400">
                    {m.id}
                  </td>
                  <td className="p-2 border border-gray-200 font-medium">
                    {m.medicine}
                  </td>
                  <td className="p-2 border border-gray-200">
                    {m.dose_notes || "—"}
                  </td>
                  <td className="p-2 border border-gray-200">
                    {m.schedule || "—"}
                  </td>
                  <td className="p-2 border border-gray-200 text-gray-400">
                    {m.added?.slice(0, 10)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Delete */}
        <div className="flex gap-2 items-center pt-2">
          <input
            value={deleteId}
            onChange={(e) => setDeleteId(e.target.value)}
            placeholder="Enter ID to delete"
            className="input-field w-40"
          />
          <button
            onClick={handleDelete}
            className="px-4 py-1.5 rounded-full bg-red-500 text-white text-sm hover:bg-red-600 transition-colors"
          >
            🗑 Delete
          </button>
        </div>
      </section>

      <style jsx>{`
        .btn-primary {
          @apply px-4 py-1.5 rounded-full bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors;
        }
        .btn-secondary {
          @apply px-4 py-1.5 rounded-full border border-gray-300 text-gray-700 text-sm hover:bg-gray-50 transition-colors;
        }
        .input-field {
          @apply w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-300;
        }
      `}</style>
    </div>
  );
}
