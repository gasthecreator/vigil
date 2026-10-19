"use client";

import { useState } from "react";

export function ReadAloudButton({ text, verified }: { text: string; verified: boolean }) {
  const [status, setStatus] = useState("");

  function speak() {
    if (!verified || !text.trim()) {
      setStatus("Read-aloud is unavailable because this explanation has not passed verification.");
      return;
    }
    if (typeof window === "undefined" || !window.speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") {
      setStatus("Read-aloud is not supported by this browser. The explanation remains available as text.");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-NG";
    utterance.onstart = () => setStatus("Reading the verified explanation aloud.");
    utterance.onend = () => setStatus("Read-aloud finished.");
    utterance.onerror = () => setStatus("Read-aloud could not start. The explanation remains available as text.");
    window.speechSynthesis.speak(utterance);
  }

  function stop() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    setStatus("Read-aloud stopped.");
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" onClick={speak} disabled={!verified} className="min-h-11 rounded border border-slate-400 px-3 py-2 text-sm font-semibold disabled:opacity-50" aria-label="Read verified explanation aloud">
        Read aloud
      </button>
      <button type="button" onClick={stop} className="min-h-11 rounded px-3 py-2 text-sm underline" aria-label="Stop read aloud">Stop</button>
      <span className="sr-only" role="status" aria-live="polite">{status}</span>
    </div>
  );
}
