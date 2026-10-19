"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";

type Facility = { facility_id: string; name: string; tier: string; illustrative: boolean };
type Range = { lo: number; hi: number };
type Rung = {
  modality: string;
  evidence_ids: string[];
  populations: string[];
  includes_breast_population: boolean;
  sensitivity: Range;
  specificity: Range;
  probability_remaining_after_negative: Range;
  price_band: number;
  turnaround_days: number;
  availability_confidence: string;
  confirm_availability: boolean;
};
type Ladder = {
  outcome: string;
  facility_id: string;
  illustrative_facility: boolean;
  rungs: Rung[];
  referrals: Array<{ facility_id: string; name: string; illustrative: boolean }>;
  skipped: Array<{ modality: string; reason: string }>;
  negative_result_statement: string;
  scope_statement: string;
};

async function request(path: string, body?: unknown) {
  const response = await fetch(`${API_BASE}/api/v1/test-ladder${path}`, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json", "X-Vigil-Role": "clinician", "X-Vigil-User-Id": "m4-workstation" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${response.status})`);
  return data;
}

function pct(range: Range) {
  return `${(range.lo * 100).toFixed(0)}–${(range.hi * 100).toFixed(0)}%`;
}

export default function TestLadderPage() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [facilityId, setFacilityId] = useState("TEMPLATE-TERTIARY");
  const [organ, setOrgan] = useState("liver");
  const [prior, setPrior] = useState("");
  const [maxPriceBand, setMaxPriceBand] = useState("4");
  const [result, setResult] = useState<Ladder | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [feedback, setFeedback] = useState({ modality: "", available: "", turnaround: "", price: "", source: "" });

  useEffect(() => {
    request("/facilities").then(setFacilities).catch((error) => setMessage(error.message));
  }, []);

  async function recommend(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const data = await request("/recommend", {
        organ,
        prior: { value: Number(prior), provenance: "Clinician-entered estimate for this decision; not a patient risk score" },
        facility_id: facilityId,
        max_price_band: Number(maxPriceBand),
      });
      setResult(data);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Recommendation unavailable");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  async function submitFeedback(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      const data = await request("/feedback", {
        facility_id: facilityId,
        modality: feedback.modality,
        available: feedback.available === "true",
        turnaround_days: feedback.turnaround ? Number(feedback.turnaround) : null,
        price_band: Number(feedback.price),
        source: feedback.source,
        verified_on: new Date().toISOString().slice(0, 10),
      });
      setMessage(`Availability and cost feedback recorded (${data.feedback_id}) and audit logged. It does not replace the illustrative registry row.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Feedback could not be recorded");
    }
  }

  const selected = facilities.find((facility) => facility.facility_id === facilityId);

  return (
    <section className="mx-auto w-full max-w-5xl space-y-6" data-testid="test-ladder-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/" className="text-sm text-emerald-800 underline">← Workstation</Link>
          <h1 className="mt-2 text-2xl font-bold">M4 Resource-Aware Test Ladder</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">Evidence-informed options for clinician review. This is decision support and does not order tests or diagnose disease.</p>
        </div>
        <span className="rounded border border-amber-400 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-950">Illustrative facility templates only</span>
      </div>

      <form onSubmit={recommend} className="grid gap-4 rounded-lg border bg-white p-5 sm:grid-cols-2 lg:grid-cols-3">
        <label className="grid gap-1 text-sm font-medium">Facility template
          <select aria-label="Facility template" value={facilityId} onChange={(event) => setFacilityId(event.target.value)} className="rounded border p-2">
            {facilities.map((facility) => <option key={facility.facility_id} value={facility.facility_id}>{facility.name} · illustrative</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-sm font-medium">Organ under review
          <select aria-label="Organ under review" value={organ} onChange={(event) => setOrgan(event.target.value)} className="rounded border p-2">
            {["bone", "liver", "lung", "brain"].map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-sm font-medium">Clinician-entered prior estimate
          <input aria-label="Clinician-entered prior estimate" type="number" min="0.01" max="0.99" step="0.01" value={prior} onChange={(event) => setPrior(event.target.value)} className="rounded border p-2" required />
        </label>
        <label className="grid gap-1 text-sm font-medium">Maximum price band (1–4)
          <select aria-label="Maximum price band" value={maxPriceBand} onChange={(event) => setMaxPriceBand(event.target.value)} className="rounded border p-2">
            {[1, 2, 3, 4].map((band) => <option key={band} value={band}>{band}</option>)}
          </select>
        </label>
        <div className="flex items-end"><button disabled={loading} className="min-h-11 rounded bg-emerald-800 px-4 py-2 font-semibold text-white disabled:opacity-50">{loading ? "Building ladder…" : "Show evidence-based options"}</button></div>
      </form>

      {selected?.illustrative && <p className="rounded border border-amber-300 bg-amber-50 p-3 text-sm" role="status">{selected.name} is an illustrative template. Its availability and cost values are not verified for a real facility.</p>}
      {message && <p role="status" className="rounded border border-slate-300 bg-slate-50 p-3 text-sm">{message}</p>}

      {result && <section aria-label="Test ladder results" className="space-y-4" data-testid="ladder-results">
        <div className="rounded border-l-4 border-rose-700 bg-rose-50 p-4 font-semibold" data-testid="negative-result-warning">{result.negative_result_statement}</div>
        <p className="text-sm text-slate-600">{result.scope_statement}</p>
        {result.illustrative_facility && <p className="text-sm font-semibold text-amber-900">Illustrative result: verify local availability, price, and turnaround before relying on this ladder.</p>}
        {result.rungs.length === 0 ? <p className="rounded border p-4">No sourced informative option is available in this facility template for the selected organ. The ladder does not treat this as a negative finding.</p> : result.rungs.map((rung, index) => <article key={rung.modality} className="rounded-lg border bg-white p-4" data-testid="ladder-rung">
          <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-bold">{index + 1}. {rung.modality.replaceAll("_", " ")}</h2><span className={`rounded px-2 py-1 text-xs font-bold ${rung.availability_confidence === "fresh" ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-950"}`}>{rung.availability_confidence === "stale" ? "Stale availability — confirm" : rung.availability_confidence === "unverified" ? "Unverified availability" : "Fresh availability"}</span></div>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="font-semibold">Sensitivity evidence range</dt><dd>{pct(rung.sensitivity)}</dd></div>
            <div><dt className="font-semibold">Specificity evidence range</dt><dd>{pct(rung.specificity)}</dd></div>
            <div><dt className="font-semibold">Residual probability after a negative result</dt><dd>{pct(rung.probability_remaining_after_negative)}</dd></div>
            <div><dt className="font-semibold">Evidence sources</dt><dd>{rung.evidence_ids.join(", ")}</dd></div>
            <div><dt className="font-semibold">Evidence population</dt><dd>{rung.populations.join("; ")}</dd></div>
            <div><dt className="font-semibold">Breast-cancer population included</dt><dd>{rung.includes_breast_population ? "Yes" : "No; applicability is indirect"}</dd></div>
          </dl>
        </article>)}
      </section>}

      <form onSubmit={submitFeedback} className="space-y-3 rounded-lg border bg-white p-5" aria-label="Availability and cost feedback">
        <div><h2 className="text-lg font-bold">Report local availability and cost</h2><p className="text-sm text-slate-600">Feedback is stored as an append-only audited report. It does not silently change evidence or recommendations.</p></div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <label className="grid gap-1 text-sm">Modality<input aria-label="Feedback modality" value={feedback.modality} onChange={(event) => setFeedback({ ...feedback, modality: event.target.value })} className="rounded border p-2" required /></label>
          <label className="grid gap-1 text-sm">Available<select aria-label="Feedback availability" value={feedback.available} onChange={(event) => setFeedback({ ...feedback, available: event.target.value })} className="rounded border p-2" required><option value="">Select availability</option><option value="true">Yes</option><option value="false">No</option></select></label>
          <label className="grid gap-1 text-sm">Turnaround days<input aria-label="Feedback turnaround days" type="number" min="0" max="365" value={feedback.turnaround} onChange={(event) => setFeedback({ ...feedback, turnaround: event.target.value })} className="rounded border p-2" /></label>
          <label className="grid gap-1 text-sm">Price band (1–4)<select aria-label="Feedback price band" value={feedback.price} onChange={(event) => setFeedback({ ...feedback, price: event.target.value })} className="rounded border p-2" required><option value="">Select price band</option>{[1, 2, 3, 4].map((band) => <option key={band}>{band}</option>)}</select></label>
          <label className="grid gap-1 text-sm">Verification source<input aria-label="Verification source" value={feedback.source} onChange={(event) => setFeedback({ ...feedback, source: event.target.value })} className="rounded border p-2" required /></label>
        </div>
        <button className="min-h-11 rounded border border-emerald-800 px-4 py-2 font-semibold text-emerald-900">Record audited feedback</button>
      </form>
    </section>
  );
}
