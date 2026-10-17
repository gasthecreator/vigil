"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslation, Button, Card, CardHeader, CardTitle, CardContent, Badge, Input } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import { CaregiverShareResponse } from "@/lib/types";
import {
  ArrowLeft,
  Share2,
  ShieldCheck,
  UserCheck,
  Trash2,
  Copy,
  Check,
  AlertTriangle,
  Clock,
  Link as LinkIcon,
} from "lucide-react";

export default function CaregiverSharePage() {
  const patientId = "PAT-001";
  const { t } = useTranslation();

  const [caregiverName, setCaregiverName] = useState<string>("");
  const [relationshipType, setRelationshipType] = useState<string>("daughter");
  const [scope, setScope] = useState<string>("view_summary");
  const [durationDays, setDurationDays] = useState<number>(14);

  const [shares, setShares] = useState<CaregiverShareResponse[]>([]);
  const [createdShare, setCreatedShare] = useState<CaregiverShareResponse | null>(null);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadShares() {
      try {
        const list = await apiClient.listCaregiverShares(patientId);
        setShares(list || []);
      } catch (err) {
        console.warn("Could not load caregiver shares:", err);
      }
    }
    loadShares();
  }, [patientId]);

  const handleCreateShare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caregiverName) return;
    setIsCreating(true);
    setError(null);

    try {
      const resp = await apiClient.createCaregiverShare(patientId, {
        caregiver_name: caregiverName,
        relationship_type: relationshipType,
        scope,
        expires_in_days: durationDays,
      });
      setCreatedShare(resp);
      setShares((prev) => [resp, ...prev]);
      setCaregiverName("");
    } catch (err: any) {
      console.error("Failed to create caregiver share:", err);
      setError(err?.message || "Failed to create caregiver access token.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevokeShare = async (shareId: string) => {
    try {
      await apiClient.revokeCaregiverShare(patientId, shareId);
      setShares((prev) =>
        prev.map((s) => (s.id === shareId ? { ...s, status: "revoked" } : s))
      );
    } catch (err) {
      console.error("Failed to revoke share:", err);
    }
  };

  const copyShareLink = (token: string) => {
    const link = `${window.location.origin}/companion/share?token=${token}`;
    navigator.clipboard?.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Back to Dashboard */}
      <Link
        href="/companion"
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Dashboard</span>
      </Link>

      {/* Sharing Invite Form */}
      <Card className="border-slate-200 overflow-hidden shadow-sm">
        <CardHeader className="bg-slate-50 border-b border-slate-200 py-4 px-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center shrink-0">
              <Share2 className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold text-slate-900">
                {t.companion.caregiverSharingTitle}
              </CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                Grant scoped, time-limited, revocable surveillance tracking access to family.
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-6">
          <form onSubmit={handleCreateShare} className="space-y-5">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Caregiver / Family Member Name
                </label>
                <input
                  type="text"
                  value={caregiverName}
                  onChange={(e) => setCaregiverName(e.target.value)}
                  placeholder="e.g. Amina Bello"
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Relationship to Patient
                </label>
                <select
                  id="relationship-select"
                  value={relationshipType}
                  onChange={(e) => setRelationshipType(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                >
                  <option value="daughter">Daughter</option>
                  <option value="son">Son</option>
                  <option value="spouse">Spouse / Partner</option>
                  <option value="sister">Sister</option>
                  <option value="brother">Brother</option>
                  <option value="caregiver">Professional Caregiver</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Access Scope
                </label>
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                >
                  <option value="view_summary">Summary View (Latest 3 labs + status)</option>
                  <option value="full_history">Full Longitudinal History</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Authorization Duration
                </label>
                <select
                  value={durationDays}
                  onChange={(e) => setDurationDays(Number(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                >
                  <option value={7}>7 Days</option>
                  <option value={14}>14 Days</option>
                  <option value={30}>30 Days (Recommended)</option>
                  <option value={90}>90 Days</option>
                </select>
              </div>
            </div>

            {/* Generated Link Alert */}
            {createdShare && (
              <div className="p-4 bg-teal-50 border border-teal-200 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-teal-900">
                  <span>Caregiver Access Link Generated</span>
                  <Badge variant="success">Active</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={`${typeof window !== "undefined" ? window.location.origin : ""}/companion/share?token=${createdShare.share_token}`}
                    className="flex-1 bg-white border border-teal-300 text-xs text-slate-800 px-3 py-2 rounded-lg font-mono"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => copyShareLink(createdShare.share_token)}
                    className="shrink-0 bg-white"
                  >
                    {copied ? (
                      <span className="flex items-center gap-1 text-emerald-600">
                        <Check className="w-3.5 h-3.5" /> Copied
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Copy className="w-3.5 h-3.5" /> Copy Link
                      </span>
                    )}
                  </Button>
                </div>
                <p className="text-[11px] text-teal-800">
                  Share this link with {createdShare.caregiver_name}. Access expires on {new Date(createdShare.expires_at).toLocaleDateString()}.
                </p>
              </div>
            )}

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                disabled={isCreating}
                className="w-full sm:w-auto bg-teal-700 hover:bg-teal-800"
              >
                <Share2 className="w-4 h-4 mr-2" />
                {isCreating ? "Generating Token..." : "Generate Caregiver Access Link"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Existing Shares Table */}
      <Card className="border-slate-200 overflow-hidden shadow-sm">
        <CardHeader className="bg-slate-50 border-b border-slate-200 py-3.5 px-6">
          <CardTitle className="text-sm font-bold text-slate-800">
            Active & Past Family Authorizations
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 divide-y divide-slate-100">
          {shares.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No caregiver shares created yet. Use the form above to share access.
            </div>
          ) : (
            shares.map((share) => (
              <div key={share.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs hover:bg-slate-50">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">
                      {share.caregiver_name}
                    </span>
                    <Badge variant={share.status === "active" ? "success" : "default"}>
                      {share.status}
                    </Badge>
                    <Badge variant="default">
                      {share.scope === "view_summary" ? "Summary Scope" : "Full History"}
                    </Badge>
                  </div>
                  <p className="text-slate-500">
                    Relationship: <span className="capitalize">{share.relationship_type}</span> • Expires: {new Date(share.expires_at).toLocaleDateString()}
                  </p>
                </div>

                {share.status === "active" && (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRevokeShare(share.id)}
                      className="text-rose-700 hover:text-rose-800 hover:bg-rose-50 border-rose-200"
                    >
                      <Trash2 className="w-3.5 h-3.5 mr-1" />
                      Revoke Access
                    </Button>
                  </div>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
