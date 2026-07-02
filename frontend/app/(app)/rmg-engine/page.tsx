"use client";
import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useRmgPipeline, useRmgExtensions, useRmgEmailRequests, useKbStatus,
  useRmgRecommendations, useRecCacheStatus, useExtensionNeeds,
  type PipelineProject, type PipelineRole, type RmgCandidate, type KbProof,
  type ExtensionNeedProject, type LeavingResource,
} from "@/lib/hooks";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Search, Sparkles, Loader2, AlertTriangle, Database, CheckCircle2,
  Mail, TrendingUp, Calendar, Zap, Users, RefreshCw, Clock,
  ChevronDown, ChevronRight, X, UserCheck, Briefcase, FileText, Send,
} from "lucide-react";


// ── Types ──────────────────────────────────────────────────────────────────
type TabType = "pipeline" | "extensions" | "changes";
type ToastType = "success" | "error" | "info";
interface Toast { id: number; type: ToastType; message: string }
interface RoleRecommendResult {
  available: RmgCandidate[];
  best_match: RmgCandidate[];
  no_resource: boolean;
  hire_signal: string | null;
  kb_active: boolean;
  total_evaluated: number;
}
interface CacheEntry {
  status: "loading" | "done" | "error";
  coe?: string;
  data?: RoleRecommendResult;
}


// ── Toast ──────────────────────────────────────────────────────────────────
function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  if (!toasts.length) return null;
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-2xl shadow-xl backdrop-blur-sm animate-in slide-in-from-bottom-2 duration-200 border ${
            t.type === "success" ? "bg-emerald-50/90 border-emerald-200 text-emerald-800" :
            t.type === "error" ? "bg-red-50/90 border-red-200 text-red-800" :
            "bg-violet-50/90 border-violet-200 text-violet-800"
          }`}
        >
          {t.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> :
           t.type === "error" ? <AlertTriangle className="w-4 h-4 shrink-0" /> :
           <Sparkles className="w-4 h-4 shrink-0" />}
          <span className="text-sm font-medium flex-1">{t.message}</span>
          <button onClick={() => onDismiss(t.id)} className="shrink-0 opacity-50 hover:opacity-100">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}



// ── Candidate Card ─────────────────────────────────────────────────────────
function CandidateCard({ candidate, rank, category }: {
  candidate: RmgCandidate; rank: number; category: "Available" | "BestMatch";
}) {
  const [showRationale, setShowRationale] = useState(false);
  const score = Math.round(candidate.total_score * 100);
  const isAvail = category === "Available";

  return (
    <div className={`group relative rounded-2xl bg-white p-4 transition-all hover:shadow-md`}
      style={{ border: `1px solid ${isAvail ? "#19105B20" : "#FF619620"}` }}>
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-white"
          style={{ background: isAvail ? "#19105B" : "#FF6196" }}>{rank}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-gray-900 truncate">{candidate.job_name ?? candidate.employee_id}</p>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-gray-100 text-gray-500">{candidate.employee_id}</span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5 truncate">
            {[candidate.canonical_role, candidate.location].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xl font-bold tabular-nums" style={{ color: isAvail ? "#19105B" : "#FF6196" }}>{score}%</p>
          <p className="text-[10px] text-gray-400">{Math.round(candidate.available_pct)}% free</p>
        </div>
      </div>


      {/* Score pills */}
      <div className="flex items-center gap-1.5 mt-3 pl-11">
        {([
          ["Skill", candidate.skill_score, "bg-gray-50 text-gray-700 border-gray-200"],
          ["Comp", candidate.comp_score, "bg-gray-50 text-gray-700 border-gray-200"],
          ["Avail", candidate.avail_score, "bg-gray-50 text-gray-700 border-gray-200"],
          ["Prod", candidate.prod_score, "bg-gray-50 text-gray-600 border-gray-200"],
        ] as [string, number | null, string][]).map(([label, val, cls]) => {
          if (val == null) return null;
          return (
            <span key={label} className={`text-[10px] tabular-nums px-2 py-0.5 rounded-full border font-medium ${cls}`}>
              {label} {Math.round(val * 100)}
            </span>
          );
        })}
      </div>

      {/* KB Proofs */}
      {candidate.kb_proof?.length > 0 && (
        <div className="flex items-center gap-1.5 mt-2 pl-11 flex-wrap">
          {candidate.kb_proof.map((p, i) => (
            <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-100 font-medium">
              {p.project_id} · {Math.round(p.similarity * 100)}%
            </span>
          ))}
        </div>
      )}

      {/* Rationale */}
      {candidate.rationale && (
        <div className="mt-2 pl-11">
          <button onClick={() => setShowRationale(!showRationale)}
            className="flex items-center gap-1.5 text-[11px] font-medium text-violet-500 hover:text-violet-700">
            <Sparkles className="w-3 h-3" /> {showRationale ? "Hide" : "Show"} rationale
          </button>
          {showRationale && (
            <p className="text-xs text-gray-500 mt-2 leading-relaxed bg-gray-50 rounded-xl px-3 py-2.5 border border-gray-100">
              {candidate.rationale}
            </p>
          )}
        </div>
      )}
    </div>
  );
}


// ── Role Recommendations Panel ─────────────────────────────────────────────
function RoleRecommendations({ entry, project, role, onReload }: {
  entry: CacheEntry | undefined; project: PipelineProject; role: PipelineRole; onReload: () => void;
}) {
  return (
    <div className="px-6 pb-5 pt-4 space-y-4 bg-gradient-to-b from-gray-50/80 to-white">
      {/* Meta strip */}
      <div className="flex flex-wrap items-center gap-2 pb-3 border-b border-gray-100">
        {entry?.coe && (
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-violet-100 text-violet-700">{entry.coe}</span>
        )}
        {role.allocation_pct != null && (
          <span className="text-xs text-gray-500 bg-white px-2.5 py-1 rounded-full border border-gray-200">{role.allocation_pct}% alloc</span>
        )}
        {role.duration_weeks != null && (
          <span className="text-xs text-gray-500 bg-white px-2.5 py-1 rounded-full border border-gray-200">{role.duration_weeks}w</span>
        )}
        {project.likely_start_date && (
          <span className="text-xs text-gray-500 flex items-center gap-1 bg-white px-2.5 py-1 rounded-full border border-gray-200">
            <Calendar className="w-3 h-3" />
            {new Date(project.likely_start_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
          </span>
        )}
        {entry?.status === "error" && (
          <button onClick={onReload} className="ml-auto text-xs flex items-center gap-1.5 text-red-500 hover:text-red-700 font-medium">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        )}
      </div>


      {/* Content */}
      {!entry || entry.status === "loading" ? (
        <div className="flex items-center gap-3 py-10 justify-center text-gray-400">
          <Loader2 className="w-5 h-5 animate-spin text-violet-400" />
          <span className="text-sm font-medium">Scoring candidates…</span>
        </div>
      ) : entry.status === "error" ? (
        <div className="flex items-start gap-3 p-4 rounded-2xl bg-red-50 border border-red-100">
          <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">Could not load recommendations</p>
            <p className="text-xs text-red-600 mt-0.5">
              {!entry.coe ? "COE could not be detected." : "Scoring failed — please retry."}
            </p>
          </div>
        </div>
      ) : entry.data ? (
        <>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1.5" style={{ color: "#19105B" }}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="font-semibold">{entry.data.available.length}</span> available
            </span>
            <span className="flex items-center gap-1.5" style={{ color: "#FF6196" }}>
              <Sparkles className="w-3.5 h-3.5" />
              <span className="font-semibold">{entry.data.best_match.length}</span> best match
            </span>
            <span className="text-gray-300">|</span>
            <span>{entry.data.total_evaluated} evaluated</span>
          </div>

          {entry.data.available.length > 0 && (
            <section className="space-y-2">
              <p className="text-xs font-semibold flex items-center gap-1.5" style={{ color: "#19105B" }}>
                <CheckCircle2 className="w-3.5 h-3.5" /> Available ({entry.data.available.length})
              </p>
              {entry.data.available.map((c, i) => <CandidateCard key={c.employee_id} candidate={c} rank={i+1} category="Available" />)}
            </section>
          )}

          {entry.data.best_match.length > 0 && (
            <section className="space-y-2">
              <p className="text-xs font-semibold flex items-center gap-1.5" style={{ color: "#FF6196" }}>
                <Sparkles className="w-3.5 h-3.5" /> Best Match ({entry.data.best_match.length})
              </p>
              {entry.data.best_match.map((c, i) => <CandidateCard key={c.employee_id} candidate={c} rank={i+1} category="BestMatch" />)}
            </section>
          )}

          {entry.data.no_resource && (
            <div className="flex items-start gap-3 p-4 rounded-2xl bg-amber-50 border border-amber-100">
              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-amber-900">No Resource — Hire Signal</p>
                <p className="text-[11px] text-amber-700 mt-1 leading-relaxed">{entry.data.hire_signal}</p>
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}


// ── Role Row ───────────────────────────────────────────────────────────────
function RoleRow({ role, roleKey, project, isRoleOpen, entry, onToggleRole, onReloadRole }: {
  role: PipelineRole; roleKey: string; project: PipelineProject;
  isRoleOpen: boolean; entry: CacheEntry | undefined;
  onToggleRole: (key: string, project: PipelineProject, role: PipelineRole) => void;
  onReloadRole: (key: string, project: PipelineProject, role: PipelineRole) => void;
}) {
  const isNR = role.status === "Not Resourced";
  const isPR = role.status === "Part Resourced";

  return (
    <>
      <tr
        onClick={isNR || isPR ? () => onToggleRole(roleKey, project, role) : undefined}
        className={`transition-all ${isNR || isPR ? "cursor-pointer hover:bg-violet-50/30" : ""} ${isRoleOpen ? "bg-violet-50/40" : ""}`}
      >
        <td className="px-4 py-3">
          <p className={`text-sm truncate ${isNR ? "font-semibold text-gray-900" : "font-medium text-gray-600"}`}>
            {role.role_code_raw ?? "—"}
          </p>
          {role.required_skills && (
            <p className="text-[10px] text-gray-400 mt-0.5 truncate max-w-[200px]">{role.required_skills}</p>
          )}
        </td>
        <td className="px-3 py-3 text-center tabular-nums text-xs text-gray-500">
          {role.allocation_pct != null ? `${role.allocation_pct}%` : "—"}
        </td>
        <td className="px-3 py-3 text-center tabular-nums text-xs text-gray-500">
          {role.duration_weeks != null ? `${role.duration_weeks}w` : "—"}
        </td>
        <td className="px-3 py-3 text-center">
          {isNR ? (
            <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full whitespace-nowrap" style={{ background: "#FF619615", color: "#FF6196", border: "1px solid #FF619630" }}>Not Resourced</span>
          ) : isPR ? (
            <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 border border-amber-100 whitespace-nowrap">Part Resourced</span>
          ) : (
            <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full inline-flex items-center gap-1 whitespace-nowrap" style={{ background: "#19105B10", color: "#19105B", border: "1px solid #19105B20" }}>
              <UserCheck className="w-3 h-3" /> Resourced
            </span>
          )}
        </td>


        <td className="px-4 py-3">
          {!isNR && !isPR ? (
            role.resourced_employee_id ? (
              <span className="text-xs font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                {role.resourced_employee_id}
              </span>
            ) : (
              <span className="text-xs text-gray-300">—</span>
            )
          ) : !entry || entry.status === "loading" ? (
            <span className="flex items-center gap-1.5 text-xs text-gray-400">
              <Loader2 className="w-3 h-3 animate-spin" /> Scoring…
            </span>
          ) : entry.status === "error" ? (
            <button onClick={e => { e.stopPropagation(); onReloadRole(roleKey, project, role); }}
              className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 font-medium">
              <AlertTriangle className="w-3 h-3" /> Retry
            </button>
          ) : entry.data?.no_resource ? (
            <span className="flex items-center gap-1.5 text-xs text-amber-600 font-medium">
              <AlertTriangle className="w-3 h-3" /> Hire signal
            </span>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              {(entry.data?.available?.length ?? 0) > 0 && (
                <span className="flex items-center gap-1 text-xs" style={{ color: "#19105B" }}>
                  <CheckCircle2 className="w-3 h-3" />{entry.data!.available.length}
                </span>
              )}
              {(entry.data?.best_match?.length ?? 0) > 0 && (
                <span className="flex items-center gap-1 text-xs" style={{ color: "#FF6196" }}>
                  <Sparkles className="w-3 h-3" />{entry.data!.best_match.length}
                </span>
              )}
              {[...entry.data!.available, ...entry.data!.best_match].slice(0, 2).map(c => (
                <span key={c.employee_id} className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-violet-50 text-violet-600 border border-violet-100">
                  {c.employee_id}
                </span>
              ))}
            </div>
          )}
        </td>
        <td className="pr-3 py-3 w-8">
          {(isNR || isPR) && (
            isRoleOpen ? <ChevronDown className="w-4 h-4 text-violet-500" /> : <ChevronRight className="w-4 h-4 text-gray-300" />
          )}
        </td>
      </tr>
      {isRoleOpen && (
        <tr><td colSpan={6} className="p-0">
          <RoleRecommendations entry={entry} project={project} role={role} onReload={() => onReloadRole(roleKey, project, role)} />
        </td></tr>
      )}
    </>
  );
}


// ── Send Recommendation Button ─────────────────────────────────────────────
function SendRecommendationBtn({ project, recCache }: { project: PipelineProject; recCache: Record<string, CacheEntry> }) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [email, setEmail] = useState("");
  const [showInput, setShowInput] = useState(false);

  const [error, setError] = useState("");

  const handleSend = async () => {
    if (!email) return;
    setSending(true);
    setError("");
    const roles = project.roles
      .filter(r => r.status === "Not Resourced")
      .map(r => {
        const entry = recCache[`${project.client_name}::${r.id}`];
        const candidates = [...(entry?.data?.available ?? []), ...(entry?.data?.best_match ?? [])].map(c => ({
          employee_id: c.employee_id, job_name: c.job_name, score: Math.round(c.total_score * 100), category: c.category,
        }));
        return { role_code: r.role_code_raw ?? "Unknown", candidates };
      })
      .filter(r => r.candidates.length > 0);

    if (roles.length === 0) {
      setError("No candidates loaded yet — expand roles first.");
      setSending(false);
      return;
    }

    try {
      const res = await api.post("/api/rmg/send-recommendation", { client_name: project.client_name, to_email: email, roles });
      if (res.data?.status === "error") { setError(res.data.message || "Send failed"); }
      else { setSent(true); setTimeout(() => { setSent(false); setShowInput(false); }, 3000); }
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || "Send failed");
    }
    setSending(false);
  };

  if (sent) return (
    <div className="px-4 py-3 flex items-center gap-2 border-t border-gray-100 text-xs text-emerald-600 font-medium">
      <CheckCircle2 className="w-3.5 h-3.5" /> Sent successfully
    </div>
  );

  return (
    <div className="px-4 py-3 flex flex-col gap-2 border-t border-gray-100">
      {error && (
        <p className="text-xs text-red-600 flex items-center gap-1.5"><AlertTriangle className="w-3 h-3" />{error}</p>
      )}
      {!showInput ? (
        <button onClick={() => setShowInput(true)}
          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg text-violet-600 hover:bg-violet-50 transition-all border border-violet-200 w-fit">
          <Send className="w-3 h-3" /> Send Recommendation
        </button>
      ) : (
        <div className="flex items-center gap-2 flex-1">
          <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Recipient email"
            className="flex-1 max-w-xs text-xs px-3 py-1.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-300" />
          <button onClick={handleSend} disabled={sending || !email}
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg text-white disabled:opacity-50 transition-all"
            style={{ background: "#19105B" }}>
            {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
            Send
          </button>
          <button onClick={() => setShowInput(false)} className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
        </div>
      )}
    </div>
  );
}

// ── Pipeline Accordion ─────────────────────────────────────────────────────
function PipelineAccordion({ projects, recCache, expandedClients, expandedRoleKey,
  onToggleClient, onToggleRole, onReloadRole, onExpandAll, onCollapseAll, search, setSearch, showNROnly, setShowNROnly,
}: {
  projects: PipelineProject[]; recCache: Record<string, CacheEntry>;
  expandedClients: Set<string>; expandedRoleKey: string | null;
  onToggleClient: (name: string) => void;
  onToggleRole: (key: string, project: PipelineProject, role: PipelineRole) => void;
  onReloadRole: (key: string, project: PipelineProject, role: PipelineRole) => void;
  onExpandAll: () => void; onCollapseAll: () => void;
  search: string; setSearch: (s: string) => void;
  showNROnly: boolean; setShowNROnly: (v: boolean) => void;
}) {
  const nrCount = projects.reduce((n, p) => n + p.roles.filter(r => r.status === "Not Resourced").length, 0);

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
      {/* Toolbar */}
      <div className="px-6 py-3 shrink-0 border-b border-gray-100 bg-white/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search client…"
              className="w-full pl-9 pr-3 py-2 text-sm rounded-xl bg-gray-50 border border-gray-200 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-300 transition-all"
            />
          </div>
          <button onClick={() => setShowNROnly(!showNROnly)}
            className={`text-xs font-semibold px-3 py-2 rounded-xl border transition-all ${
              showNROnly ? "bg-red-50 border-red-200 text-red-600" : "bg-white border-gray-200 text-gray-600 hover:border-violet-200 hover:text-violet-600"
            }`}>
            Not Resourced
          </button>
          <button onClick={expandedClients.size > 0 ? onCollapseAll : onExpandAll}
            className="text-xs font-semibold px-3 py-2 rounded-xl border border-gray-200 text-gray-600 hover:border-violet-200 hover:text-violet-600 transition-all flex items-center gap-1.5">
            {expandedClients.size > 0 ? <><ChevronDown className="w-3 h-3" /> Collapse</> : <><ChevronRight className="w-3 h-3" /> Expand</>}
          </button>
          <span className="text-xs font-semibold ml-auto tabular-nums text-violet-600 bg-violet-50 px-3 py-1.5 rounded-full">
            {nrCount} open
          </span>
        </div>
      </div>


      {/* List */}
      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        {projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <Briefcase className="w-10 h-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">No projects found</p>
          </div>
        ) : projects.map(project => {
          const isOpen = expandedClients.has(project.client_name);
          const nrRoles = project.roles.filter(r => r.status === "Not Resourced");

          return (
            <div key={project.client_name} className={`rounded-2xl overflow-hidden border transition-all ${
              isOpen ? "border-violet-200 shadow-sm" : "border-gray-100 hover:border-gray-200"
            }`}>
              <button onClick={() => onToggleClient(project.client_name)}
                className={`w-full flex items-center gap-3 px-5 py-4 text-left transition-all ${
                  isOpen ? "bg-gradient-to-r from-violet-50/50 to-white" : "bg-white hover:bg-gray-50/50"
                }`}>
                {isOpen ? <ChevronDown className="w-4 h-4 text-violet-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2.5">
                    <span className="text-sm font-bold text-gray-900 truncate">{project.client_name}</span>
                    {project.client_priority && (
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        project.client_priority === "Gold" ? "bg-amber-50 text-amber-700 border border-amber-200" :
                        project.client_priority === "Silver" ? "bg-gray-50 text-gray-600 border border-gray-200" :
                        "bg-orange-50 text-orange-700 border border-orange-200"
                      }`}>{project.client_priority}</span>
                    )}
                  </div>
                  <p className="text-[11px] text-gray-400 mt-0.5">
                    {[project.solution, project.deal_stage].filter(Boolean).join(" · ")}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {project.likely_start_date && (
                    <span className="text-[11px] text-gray-400 flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(project.likely_start_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                    </span>
                  )}
                  {project.probability_weight != null && (
                    <span className="text-xs font-bold tabular-nums text-violet-600">{Math.round(project.probability_weight * 100)}%</span>
                  )}
                  {nrRoles.length > 0 && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-50 text-red-600 border border-red-100">
                      {nrRoles.length} open
                    </span>
                  )}
                  <span className="text-[11px] text-gray-400">{project.role_count} roles</span>
                </div>
              </button>


              {isOpen && (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-t border-gray-100 bg-gray-50/50">
                        <th className="px-4 py-2.5 text-left font-semibold text-gray-500 uppercase tracking-wider text-[10px] w-[200px]">Role</th>
                        <th className="px-3 py-2.5 text-center font-semibold text-gray-500 uppercase tracking-wider text-[10px] w-[60px]">Alloc</th>
                        <th className="px-3 py-2.5 text-center font-semibold text-gray-500 uppercase tracking-wider text-[10px] w-[50px]">Dur</th>
                        <th className="px-3 py-2.5 text-center font-semibold text-gray-500 uppercase tracking-wider text-[10px] w-[110px]">Status</th>
                        <th className="px-4 py-2.5 text-left font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Recommendation</th>
                        <th className="w-8" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {project.roles.map(role => {
                        const roleKey = `${project.client_name}::${role.id}`;
                        return (
                          <RoleRow key={role.id} role={role} roleKey={roleKey} project={project}
                            isRoleOpen={expandedRoleKey === roleKey} entry={recCache[roleKey]}
                            onToggleRole={onToggleRole} onReloadRole={onReloadRole} />
                        );
                      })}
                    </tbody>
                  </table>
                  {/* Send Recommendation button */}
                  <SendRecommendationBtn project={project} recCache={recCache} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


// ── Extensions View ────────────────────────────────────────────────────────
function ExtensionsView() {
  const { data: needs = [], isLoading } = useExtensionNeeds();
  const { data: extData } = useRmgExtensions();
  const extensions = extData?.allocation_extensions ?? [];
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [expandedResource, setExpandedResource] = useState<string | null>(null);
  const [recCache, setRecCache] = useState<Record<string, CacheEntry>>({});
  const loadingRef = useRef<Set<string>>(new Set());
  const [search, setSearch] = useState("");

  const loadRec = useCallback(async (key: string, resource: LeavingResource, coe: string | null) => {
    if (loadingRef.current.has(key)) return;
    loadingRef.current.add(key);
    setRecCache(prev => ({ ...prev, [key]: { status: "loading" } }));
    try {
      const params = new URLSearchParams();
      if (resource.canonical_role && resource.canonical_role !== "nan") params.append("canonical_roles", resource.canonical_role);
      const { data: coeData } = await api.get(`/api/rmg/auto-coe?${params.toString()}`);
      const detectedCoe: string | null = coeData.coe || coe;
      if (!detectedCoe) { setRecCache(prev => ({ ...prev, [key]: { status: "error" } })); return; }
      const { data } = await api.post("/api/rmg/recommend-role", {
        role_code: resource.canonical_role ?? resource.job_name ?? "Unknown",
        canonical_roles: resource.canonical_role && resource.canonical_role !== "nan" ? [resource.canonical_role] : [],
        coe: detectedCoe,
        allocation_pct: resource.allocation_pct ?? 100,
        required_skills: null,
        with_rationale: false,
        with_kb_proof: true,
      });
      setRecCache(prev => ({ ...prev, [key]: { status: "done", coe: detectedCoe, data } }));
    } catch {
      setRecCache(prev => ({ ...prev, [key]: { status: "error" } }));
    }
  }, []);

  const handleToggleResource = useCallback((key: string, resource: LeavingResource, coe: string | null) => {
    setExpandedResource(prev => {
      if (prev === key) return null;
      loadRec(key, resource, coe);
      return key;
    });
  }, [loadRec]);

  const filtered = useMemo(() => {
    if (!search) return needs;
    const q = search.toLowerCase();
    return needs.filter(p => p.client_id.toLowerCase().includes(q) || p.project_id.toLowerCase().includes(q));
  }, [needs, search]);

  const totalLeaving = needs.reduce((n, p) => n + p.leaving_resources.length, 0);

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
      {/* Toolbar */}
      <div className="px-6 py-3 shrink-0 border-b border-gray-100 bg-white/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search project / client…"
              className="w-full pl-9 pr-3 py-2 text-sm rounded-xl bg-gray-50 border border-gray-200 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-300 transition-all" />
          </div>
          <span className="text-xs font-semibold ml-auto tabular-nums text-violet-600 bg-violet-50 px-3 py-1.5 rounded-full">
            {totalLeaving} leaving
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-20 gap-2 text-sm text-gray-400">
            <Loader2 className="w-5 h-5 animate-spin text-violet-400" /> Loading…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <Users className="w-10 h-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">No resource gaps found</p>
          </div>
        ) : (
          <>
            {/* Resource Needs Accordion */}
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <Users className="w-4 h-4 text-violet-500" />
                Resource Needs — Replacement Required ({totalLeaving})
              </h2>
              {filtered.map(project => {
                const isOpen = expandedProject === project.project_id;
                return (
                  <div key={project.project_id} className={`rounded-2xl overflow-hidden border transition-all ${isOpen ? "border-violet-200 shadow-sm" : "border-gray-100 hover:border-gray-200"}`}>
                    <button onClick={() => setExpandedProject(isOpen ? null : project.project_id)}
                      className={`w-full flex items-center gap-3 px-5 py-4 text-left transition-all ${isOpen ? "bg-gradient-to-r from-violet-50/50 to-white" : "bg-white hover:bg-gray-50/50"}`}>
                      {isOpen ? <ChevronDown className="w-4 h-4 text-violet-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2.5">
                          <span className="text-sm font-bold text-gray-900 truncate">{project.client_id}</span>
                          {project.proposition_coe && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-violet-50 text-violet-600 border border-violet-100">{project.proposition_coe}</span>
                          )}
                        </div>
                        <p className="text-[11px] text-gray-400 mt-0.5">{project.project_id}</p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        {project.project_end_date && (
                          <span className="text-[11px] text-gray-400 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            Ends {new Date(project.project_end_date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "2-digit" })}
                          </span>
                        )}
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-50 text-red-600 border border-red-100">
                          {project.leaving_resources.length} leaving
                        </span>
                      </div>
                    </button>

                    {isOpen && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-t border-gray-100 bg-gray-50/50">
                              <th className="px-4 py-2.5 text-left font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Employee</th>
                              <th className="px-3 py-2.5 text-left font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Role</th>
                              <th className="px-3 py-2.5 text-center font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Alloc</th>
                              <th className="px-3 py-2.5 text-center font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Ends</th>
                              <th className="px-3 py-2.5 text-center font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Gap</th>
                              <th className="px-4 py-2.5 text-left font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Replacement</th>
                              <th className="w-8" />
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-50">
                            {project.leaving_resources.map(res => {
                              const resKey = `${project.project_id}::${res.employee_id}`;
                              const isResOpen = expandedResource === resKey;
                              const entry = recCache[resKey];
                              return (
                                <React.Fragment key={res.employee_id}>
                                  <tr onClick={() => handleToggleResource(resKey, res, project.proposition_coe)}
                                    className={`cursor-pointer transition-all hover:bg-violet-50/30 ${isResOpen ? "bg-violet-50/40" : ""}`}>
                                    <td className="px-4 py-3">
                                      <p className="text-sm font-semibold text-gray-900">{res.job_name && res.job_name !== "nan" ? res.job_name : res.employee_id}</p>
                                      <p className="text-[10px] text-gray-400 font-mono">{res.employee_id}</p>
                                    </td>
                                    <td className="px-3 py-3 text-gray-600">{res.canonical_role && res.canonical_role !== "nan" ? res.canonical_role : "—"}</td>
                                    <td className="px-3 py-3 text-center tabular-nums text-gray-500">{res.allocation_pct != null ? `${res.allocation_pct}%` : "—"}</td>
                                    <td className="px-3 py-3 text-center tabular-nums text-gray-500">
                                      {res.alloc_end_date ? new Date(res.alloc_end_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "—"}
                                    </td>
                                    <td className="px-3 py-3 text-center">
                                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-50 text-red-600 border border-red-100">{res.days_gap}d</span>
                                    </td>
                                    <td className="px-4 py-3">
                                      {!entry || entry.status === "loading" ? (
                                        <span className="flex items-center gap-1.5 text-xs text-gray-400"><Loader2 className="w-3 h-3 animate-spin" /> Scoring…</span>
                                      ) : entry.status === "error" ? (
                                        <span className="flex items-center gap-1.5 text-xs text-red-500"><AlertTriangle className="w-3 h-3" /> Failed</span>
                                      ) : entry.data?.no_resource ? (
                                        <span className="flex items-center gap-1.5 text-xs text-amber-600"><AlertTriangle className="w-3 h-3" /> Hire signal</span>
                                      ) : (
                                        <div className="flex items-center gap-2">
                                          {(entry.data?.available?.length ?? 0) > 0 && (
                                            <span className="flex items-center gap-1 text-xs" style={{ color: "#19105B" }}><CheckCircle2 className="w-3 h-3" />{entry.data!.available.length}</span>
                                          )}
                                          {(entry.data?.best_match?.length ?? 0) > 0 && (
                                            <span className="flex items-center gap-1 text-xs" style={{ color: "#FF6196" }}><Sparkles className="w-3 h-3" />{entry.data!.best_match.length}</span>
                                          )}
                                        </div>
                                      )}
                                    </td>
                                    <td className="pr-3 py-3 w-8">
                                      {isResOpen ? <ChevronDown className="w-4 h-4 text-violet-500" /> : <ChevronRight className="w-4 h-4 text-gray-300" />}
                                    </td>
                                  </tr>
                                  {isResOpen && (
                                    <tr><td colSpan={7} className="p-0">
                                      <div className="px-6 pb-5 pt-4 space-y-4 bg-gradient-to-b from-gray-50/80 to-white">
                                        <div className="flex flex-wrap items-center gap-2 pb-3 border-b border-gray-100">
                                          {entry?.coe && <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-violet-100 text-violet-700">{entry.coe}</span>}
                                          <span className="text-xs text-gray-500 bg-white px-2.5 py-1 rounded-full border border-gray-200">
                                            Replacing {res.canonical_role && res.canonical_role !== "nan" ? res.canonical_role : res.employee_id}
                                          </span>
                                          {res.allocation_pct != null && <span className="text-xs text-gray-500 bg-white px-2.5 py-1 rounded-full border border-gray-200">{res.allocation_pct}% alloc</span>}
                                        </div>
                                        {!entry || entry.status === "loading" ? (
                                          <div className="flex items-center gap-3 py-10 justify-center text-gray-400">
                                            <Loader2 className="w-5 h-5 animate-spin text-violet-400" />
                                            <span className="text-sm font-medium">Scoring candidates…</span>
                                          </div>
                                        ) : entry.status === "error" ? (
                                          <div className="flex items-start gap-3 p-4 rounded-2xl bg-red-50 border border-red-100">
                                            <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                                            <p className="text-sm font-semibold text-red-800">Could not load recommendations</p>
                                          </div>
                                        ) : entry.data ? (
                                          <>
                                            <div className="flex items-center gap-4 text-xs text-gray-500">
                                              <span className="flex items-center gap-1.5" style={{ color: "#19105B" }}><CheckCircle2 className="w-3.5 h-3.5" /><span className="font-semibold">{entry.data.available.length}</span> available</span>
                                              <span className="flex items-center gap-1.5" style={{ color: "#FF6196" }}><Sparkles className="w-3.5 h-3.5" /><span className="font-semibold">{entry.data.best_match.length}</span> best match</span>
                                              <span className="text-gray-300">|</span>
                                              <span>{entry.data.total_evaluated} evaluated</span>
                                            </div>
                                            {entry.data.available.length > 0 && (
                                              <section className="space-y-2">
                                                <p className="text-xs font-semibold flex items-center gap-1.5" style={{ color: "#19105B" }}><CheckCircle2 className="w-3.5 h-3.5" /> Available ({entry.data.available.length})</p>
                                                {entry.data.available.map((c, i) => <CandidateCard key={c.employee_id} candidate={c} rank={i+1} category="Available" />)}
                                              </section>
                                            )}
                                            {entry.data.best_match.length > 0 && (
                                              <section className="space-y-2">
                                                <p className="text-xs font-semibold flex items-center gap-1.5" style={{ color: "#FF6196" }}><Sparkles className="w-3.5 h-3.5" /> Best Match ({entry.data.best_match.length})</p>
                                                {entry.data.best_match.map((c, i) => <CandidateCard key={c.employee_id} candidate={c} rank={i+1} category="BestMatch" />)}
                                              </section>
                                            )}
                                            {entry.data.no_resource && (
                                              <div className="flex items-start gap-3 p-4 rounded-2xl bg-amber-50 border border-amber-100">
                                                <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                                                <div>
                                                  <p className="text-xs font-semibold text-amber-900">No Resource — Hire Signal</p>
                                                  <p className="text-[11px] text-amber-700 mt-1 leading-relaxed">{entry.data.hire_signal}</p>
                                                </div>
                                              </div>
                                            )}
                                          </>
                                        ) : null}
                                      </div>
                                    </td></tr>
                                  )}
                                </React.Fragment>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </section>

            {/* Over-Extended (existing awareness table) */}
            {extensions.length > 0 && (
              <section className="mt-6">
                <h2 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-violet-500" />
                  Over-Extended Allocations ({extensions.length})
                </h2>
                <div className="overflow-x-auto rounded-2xl border border-gray-100">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50 text-gray-500 uppercase text-[10px] tracking-wider">
                        {["Project", "Client", "COE", "Project End", "Alloc End", "Extended", "HC"].map(h => (
                          <th key={h} className="px-4 py-3 text-left font-semibold">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {extensions.slice(0, 30).map(e => (
                        <tr key={e.project_id} className="hover:bg-violet-50/30 transition-colors">
                          <td className="px-4 py-3 font-mono text-[11px] text-gray-700">{e.project_id}</td>
                          <td className="px-4 py-3 text-gray-600">{e.client_id}</td>
                          <td className="px-4 py-3 text-gray-500">{e.proposition_coe ?? "—"}</td>
                          <td className="px-4 py-3 tabular-nums text-gray-500">{e.project_end_date ? new Date(e.project_end_date).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "—"}</td>
                          <td className="px-4 py-3 tabular-nums text-gray-500">{e.max_alloc_end_date ? new Date(e.max_alloc_end_date).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "—"}</td>
                          <td className="px-4 py-3 tabular-nums font-bold text-violet-600">+{e.days_extended}d</td>
                          <td className="px-4 py-3 tabular-nums text-gray-600">{e.headcount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}


// ── Changes View ───────────────────────────────────────────────────────────
function ChangeRequestCard({ r }: { r: { id: string; source_email: string | null; received_at: string | null; request_type: string | null; parsed_json: Record<string, unknown> | null; status: string | null } }) {
  const [expanded, setExpanded] = useState(false);
  const [recEntry, setRecEntry] = useState<CacheEntry | undefined>(undefined);
  const loadedRef = useRef(false);
  const parsed = (r.parsed_json ?? {}) as Record<string, string>;
  const isExtend = r.request_type === "EXTEND";

  const loadRecommendation = useCallback(async () => {
    if (loadedRef.current || !isExtend) return;
    loadedRef.current = true;
    setRecEntry({ status: "loading" });
    try {
      const role = parsed.role || parsed.canonical_role || "Solutions Enabler";
      const params = new URLSearchParams();
      params.append("canonical_roles", role);
      const { data: coeData } = await api.get(`/api/rmg/auto-coe?${params.toString()}`);
      const coe: string | null = coeData.coe || parsed.coe || "Data Engineering";
      const { data } = await api.post("/api/rmg/recommend-role", {
        role_code: role, canonical_roles: [role], coe,
        allocation_pct: Number(parsed.allocation_pct) || 100,
        required_skills: parsed.required_skills || null,
        with_rationale: false, with_kb_proof: true,
      });
      setRecEntry({ status: "done", coe: coe || undefined, data });
    } catch { setRecEntry({ status: "error" }); loadedRef.current = false; }
  }, [isExtend, parsed]);

  const handleToggle = () => {
    if (!expanded && isExtend) loadRecommendation();
    setExpanded(!expanded);
  };

  return (
    <div className={`border rounded-2xl overflow-hidden transition-all ${expanded ? "shadow-sm" : "hover:border-gray-200"}`} style={{ borderColor: expanded ? "#19105B30" : undefined }}>
      <div className="flex items-center gap-3 px-5 py-3.5 cursor-pointer" onClick={handleToggle}>
        {expanded ? <ChevronDown className="w-4 h-4 shrink-0" style={{ color: "#19105B" }} /> : <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />}
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: isExtend ? "#19105B0f" : "#FF61960f", color: isExtend ? "#19105B" : "#FF6196", border: `1px solid ${isExtend ? "#19105B30" : "#FF619630"}` }}>{r.request_type}</span>
        <span className="text-xs text-gray-500">{r.source_email}</span>
        {parsed.client_name && <span className="text-xs font-bold" style={{ color: "#19105B" }}>{parsed.client_name}</span>}
        {parsed.project_id && <span className="text-[10px] font-mono text-gray-400">{parsed.project_id}</span>}
        <span className="text-xs text-gray-400 ml-auto">{r.received_at ? new Date(r.received_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "—"}</span>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ background: r.status === "PARSED" ? "#19105B10" : r.status === "REPLIED" ? "#05966910" : "#FFC00020", color: r.status === "PARSED" ? "#19105B" : r.status === "REPLIED" ? "#059669" : "#d97706" }}>{r.status === "REPLIED" ? "Replied" : r.status}</span>
      </div>

      {expanded && (
        <div className="border-t px-5 py-4 space-y-3" style={{ borderColor: "#19105B10" }}>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            {[
              ["Request Type", parsed.request_type || parsed.req_type],
              ["Urgency", parsed.urgency],
              ["Client", parsed.client_name],
              ["Project Code", parsed.project_id || parsed.project_code],
              ["COE", parsed.coe],
              ["Employee", parsed.employee_name || parsed.alloc_1_email],
              ["Role", parsed.role || parsed.canonical_role],
              ["Current Allocation", parsed.current_allocation_pct || parsed.alloc_1_current],
              ["New Allocation", parsed.new_allocation_pct || parsed.alloc_1_new],
              ["Start Date", parsed.start_date],
              ["End Date", parsed.end_date || parsed.new_end_date],
              ["Reporting To", parsed.reporting_to],
              ["EM Lead", parsed.delivery_em_lead],
            ].filter(([, v]) => v && String(v).trim() && String(v) !== "nan").map(([label, value]) => (
              <div key={String(label)} className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                <p className="text-[9px] font-semibold uppercase tracking-wider text-gray-400">{String(label)}</p>
                <p className="text-xs font-medium mt-0.5" style={{ color: "#19105B" }}>{String(value)}</p>
              </div>
            ))}
          </div>

          {(parsed.change_details || parsed.scope_notes || parsed.comments) && (
            <div className="rounded-lg px-3 py-2.5 border" style={{ background: "#19105B05", borderColor: "#19105B15" }}>
              <p className="text-[9px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Notes</p>
              <p className="text-xs leading-relaxed" style={{ color: "#19105B" }}>{parsed.change_details || parsed.scope_notes || parsed.comments}</p>
            </div>
          )}

          {/* AI Recommendations for EXTEND only */}
          {isExtend && (
            <div className="pt-2">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-3.5 h-3.5" style={{ color: "#19105B" }} />
                <span className="text-xs font-semibold" style={{ color: "#19105B" }}>AI Replacement Recommendations</span>
                {recEntry?.coe && <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "#19105B10", color: "#19105B" }}>{recEntry.coe}</span>}
              </div>
              {!recEntry || recEntry.status === "loading" ? (
                <div className="flex items-center gap-3 py-6 justify-center text-gray-400"><Loader2 className="w-4 h-4 animate-spin" /> Scoring candidates…</div>
              ) : recEntry.status === "error" ? (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-100 text-xs text-red-700"><AlertTriangle className="w-3.5 h-3.5" /> Could not load recommendations</div>
              ) : recEntry.data ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span style={{ color: "#19105B" }}><CheckCircle2 className="w-3.5 h-3.5 inline" /> {recEntry.data.available.length} available</span>
                    <span style={{ color: "#FF6196" }}><Sparkles className="w-3.5 h-3.5 inline" /> {recEntry.data.best_match.length} best match</span>
                    <span className="text-gray-300">|</span><span>{recEntry.data.total_evaluated} evaluated</span>
                  </div>
                  {recEntry.data.available.map((c, i) => <CandidateCard key={c.employee_id} candidate={c} rank={i+1} category="Available" />)}
                  {recEntry.data.best_match.map((c, i) => <CandidateCard key={c.employee_id} candidate={c} rank={i+1} category="BestMatch" />)}
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ChangesView() {
  const { data: requests = [], isLoading } = useRmgEmailRequests();
  const queryClient = useQueryClient();
  const changes = requests.filter(r => r.request_type === "CHANGE" || r.request_type === "NEW" || r.request_type === "EXTEND");
  const [processing, setProcessing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  const processEmails = async () => {
    setProcessing(true);
    setLogs(["Connecting to mailbox..."]);
    try {
      setLogs(prev => [...prev, "Fetching latest 'Resource Request' emails..."]);
      const res = await api.post("/api/webhooks/email/process-latest");
      const data = res.data;
      if (data.status === "error") {
        setLogs(prev => [...prev, `Error: ${data.message}`]);
      } else if (data.processed === 0) {
        setLogs(prev => [...prev, "No new emails to process."]);
      } else {
        for (const e of data.emails) {
          setLogs(prev => [...prev, `Extracting PDF from: ${e.from}...`, `Parsing with AI: "${e.subject}"...`, `Routed successfully.`]);
        }
        setLogs(prev => [...prev, `Done — ${data.processed} email(s) processed.`]);
        queryClient.invalidateQueries({ queryKey: ["rmg-email-requests"] });
        queryClient.invalidateQueries({ queryKey: ["rmg-pipeline"] });
      }
    } catch (err: any) {
      setLogs(prev => [...prev, `Failed: ${err?.message || "Unknown error"}`]);
    }
    setProcessing(false);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold flex items-center gap-2" style={{ color: "#19105B" }}>
          <Mail className="w-4 h-4" /> Change Requests ({changes.length})
        </h2>
        <button onClick={processEmails} disabled={processing}
          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg text-white disabled:opacity-50 transition-all"
          style={{ background: "#19105B" }}>
          {processing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Mail className="w-3 h-3" />}
          Process Emails
        </button>
      </div>

      {/* Processing Logs */}
      {logs.length > 0 && (
        <div className="mb-4 rounded-xl border border-gray-100 bg-gray-50 p-3 space-y-1 max-h-40 overflow-y-auto">
          {logs.map((log, i) => (
            <p key={i} className="text-[11px] font-mono flex items-center gap-2" style={{ color: "#19105B" }}>
              <span className="text-[10px] text-gray-400">{String(i + 1).padStart(2, "0")}</span>
              {log}
            </p>
          ))}
          {processing && <Loader2 className="w-3 h-3 animate-spin text-gray-400 mt-1" />}
        </div>
      )}

      {isLoading ? (
        <div className="text-xs text-gray-400 flex items-center gap-2"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading…</div>
      ) : changes.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Mail className="w-10 h-10 mx-auto mb-3 opacity-20" />
          <p className="text-sm font-medium mb-1">No change requests yet</p>
          <p className="text-xs max-w-xs mx-auto leading-relaxed">
            Send email to <span className="font-mono text-gray-500">sathishkumar@jmangroup.com</span> with subject "Resource Request"
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {changes.map(r => <ChangeRequestCard key={r.id} r={r} />)}
        </div>
      )}
    </div>
  );
}


// ── Main Page ──────────────────────────────────────────────────────────────
const TABS: { id: TabType; label: string; icon: typeof Briefcase }[] = [
  { id: "pipeline",   label: "Pipeline",   icon: Briefcase },
  { id: "extensions", label: "Extensions", icon: TrendingUp },
  { id: "changes",    label: "Changes",    icon: Mail },
];

export default function RmgEnginePage() {
  const [tab, setTab] = useState<TabType>("pipeline");
  const [search, setSearch] = useState("");
  const [showNROnly, setShowNROnly] = useState(false);
  const [showDocModal, setShowDocModal] = useState(false);
  const [expandedClients, setExpandedClients] = useState<Set<string>>(new Set());
  const [expandedRoleKey, setExpandedRoleKey] = useState<string | null>(null);
  const [recCache, setRecCache] = useState<Record<string, CacheEntry>>({});
  const loadingRef = useRef<Set<string>>(new Set());
  const initialExpandedRef = useRef(false);

  const { data: rawProjects = [], isLoading: pipelinesLoading } = useRmgPipeline();
  const { data: kbStatus } = useKbStatus();
  const { data: serverRecs } = useRmgRecommendations();
  const { data: cacheStatus } = useRecCacheStatus();
  const queryClient = useQueryClient();

  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastId = useRef(0);
  const addToast = useCallback((type: ToastType, message: string) => {
    const id = ++toastId.current;
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000);
  }, []);
  const dismissToast = useCallback((id: number) => setToasts(prev => prev.filter(t => t.id !== id)), []);

  const buildKb = useMutation({
    mutationFn: () => api.post("/api/rmg/kb/build"),
    onSuccess: (res) => { queryClient.invalidateQueries({ queryKey: ["kb-status"] }); addToast("success", res.data?.message ?? "KB built."); },
    onError: () => addToast("error", "KB build failed."),
  });
  const refreshRecs = useMutation({
    mutationFn: () => api.post("/api/rmg/recommendations/refresh"),
    onSuccess: (res) => { queryClient.invalidateQueries({ queryKey: ["rec-cache-status"] }); addToast("info", res.data?.message ?? "Refresh started."); },
    onError: () => addToast("error", "Refresh failed."),
  });


  const projects = useMemo(() => {
    let list = rawProjects;
    if (search) { const q = search.toLowerCase(); list = list.filter(p => p.client_name?.toLowerCase().includes(q)); }
    if (showNROnly) { list = list.filter(p => p.roles.some(r => r.status === "Not Resourced")); }
    return list;
  }, [rawProjects, search, showNROnly]);

  const loadRole = useCallback(async (key: string, _project: PipelineProject, role: PipelineRole) => {
    if (loadingRef.current.has(key)) return;
    loadingRef.current.add(key);
    setRecCache(prev => ({ ...prev, [key]: { status: "loading" } }));
    try {
      const params = new URLSearchParams();
      (role.canonical_roles ?? []).forEach(r => params.append("canonical_roles", r));
      const { data: coeData } = await api.get(`/api/rmg/auto-coe?${params.toString()}`);
      const coe: string | null = coeData.coe;
      if (!coe) { setRecCache(prev => ({ ...prev, [key]: { status: "error" } })); loadingRef.current.delete(key); return; }
      const { data } = await api.post("/api/rmg/recommend-role", {
        role_code: role.role_code_raw ?? "Unknown",
        canonical_roles: role.canonical_roles,
        coe, allocation_pct: role.allocation_pct ?? 100,
        required_skills: role.required_skills, with_rationale: false, with_kb_proof: true,
      });
      setRecCache(prev => ({ ...prev, [key]: { status: "done", coe, data } }));
    } catch { setRecCache(prev => ({ ...prev, [key]: { status: "error" } })); loadingRef.current.delete(key); }
  }, []);

  // Hydrate from server recs
  useEffect(() => {
    if (!serverRecs || !rawProjects.length) return;
    const toAdd: Record<string, CacheEntry> = {};
    rawProjects.forEach(p => p.roles.forEach(r => {
      const key = `${p.client_name}::${r.id}`;
      const cached = serverRecs[String(r.id)];
      if (cached && !loadingRef.current.has(key)) {
        loadingRef.current.add(key);
        toAdd[key] = { status: "done", coe: cached.coe ?? undefined, data: {
          available: cached.available, best_match: cached.best_match,
          no_resource: cached.no_resource, hire_signal: cached.hire_signal,
          kb_active: cached.kb_active, total_evaluated: cached.total_evaluated,
        }};
      }
    }));
    if (Object.keys(toAdd).length) setRecCache(prev => ({ ...toAdd, ...prev }));
  }, [serverRecs, rawProjects]);


  // Auto-expand first NR client (no background pre-load — use server recs)
  useEffect(() => {
    if (!rawProjects.length || initialExpandedRef.current) return;
    initialExpandedRef.current = true;
    const firstNR = rawProjects.find(p => p.roles.some(r => r.status === "Not Resourced"));
    if (firstNR) {
      setExpandedClients(new Set([firstNR.client_name]));
      const firstRole = firstNR.roles.find(r => r.status === "Not Resourced");
      if (firstRole) {
        const key = `${firstNR.client_name}::${firstRole.id}`;
        setExpandedRoleKey(key);
      }
    }
  }, [rawProjects]);

  const handleToggleClient = useCallback((name: string) => {
    setExpandedClients(prev => prev.has(name) ? new Set<string>() : new Set([name]));
    setExpandedRoleKey(prev => prev && !prev.startsWith(`${name}::`) ? null : prev);
  }, []);
  const handleExpandAll = useCallback(() => setExpandedClients(new Set(rawProjects.map(p => p.client_name))), [rawProjects]);
  const handleCollapseAll = useCallback(() => { setExpandedClients(new Set()); setExpandedRoleKey(null); }, []);
  const handleToggleRole = useCallback((key: string, project: PipelineProject, role: PipelineRole) => {
    setExpandedRoleKey(prev => { if (prev === key) return null; loadRole(key, project, role); return key; });
  }, [loadRole]);
  const handleReloadRole = useCallback((key: string, project: PipelineProject, role: PipelineRole) => {
    loadingRef.current.delete(key); loadRole(key, project, role);
  }, [loadRole]);

  const lastScoredLabel = useMemo(() => {
    const ts = cacheStatus?.last_computed_at;
    if (!ts) return null;
    const diffMin = Math.round((Date.now() - new Date(ts).getTime()) / 60000);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return new Date(ts).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  }, [cacheStatus?.last_computed_at]);


  return (
    <>
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-gray-100 bg-white shrink-0">
        {/* Tabs */}
        <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
                tab === id ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}>
              <Icon className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-3">
          {lastScoredLabel && !cacheStatus?.is_running && (
            <span className="text-[10px] text-gray-400 flex items-center gap-1"><Clock className="w-3 h-3" /> {lastScoredLabel}</span>
          )}
          {cacheStatus?.is_running && (
            <span className="text-[10px] text-violet-500 flex items-center gap-1 animate-pulse"><Loader2 className="w-3 h-3 animate-spin" /> Scoring…</span>
          )}
          {kbStatus && (
            <span className="text-[10px] text-gray-400 flex items-center gap-1.5"><Database className="w-3 h-3" /> {kbStatus.embeddings} KB</span>
          )}
          <Button size="sm" variant="outline" className="text-xs h-8 gap-1.5 rounded-xl"
            onClick={() => setShowDocModal(true)}>
            <FileText className="w-3 h-3" /> How It Works
          </Button>
          <Button size="sm" variant="outline" className="text-xs h-8 gap-1.5 rounded-xl"
            onClick={() => refreshRecs.mutate()} disabled={refreshRecs.isPending || cacheStatus?.is_running}>
            {refreshRecs.isPending || cacheStatus?.is_running ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            Refresh
          </Button>
          <Button size="sm" variant="outline" className="text-xs h-8 gap-1.5 rounded-xl"
            onClick={() => buildKb.mutate()} disabled={buildKb.isPending}>
            {buildKb.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
            Build KB
          </Button>
        </div>
      </div>

      {/* Content */}
      {tab === "pipeline" && (
        pipelinesLoading ? (
          <div className="flex-1 flex items-center justify-center gap-2 text-sm text-gray-400">
            <Loader2 className="w-5 h-5 animate-spin text-violet-400" /> Loading pipeline…
          </div>
        ) : (
          <PipelineAccordion projects={projects} recCache={recCache}
            expandedClients={expandedClients} expandedRoleKey={expandedRoleKey}
            onToggleClient={handleToggleClient} onToggleRole={handleToggleRole}
            onReloadRole={handleReloadRole} onExpandAll={handleExpandAll} onCollapseAll={handleCollapseAll}
            search={search} setSearch={setSearch} showNROnly={showNROnly} setShowNROnly={setShowNROnly} />
        )
      )}
      {tab === "extensions" && <ExtensionsView />}
      {tab === "changes" && <ChangesView />}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      {showDocModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowDocModal(false)}>
          <div className="relative w-[92vw] h-[90vh] bg-white shadow-2xl flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-3 shrink-0" style={{ background: "#19105B" }}>
              <div className="flex items-center gap-3">
                <Sparkles className="w-4 h-4 text-white" />
                <span className="text-sm font-bold text-white">AI Recommendation Engine — How It Works</span>
              </div>
              <button onClick={() => setShowDocModal(false)} className="w-8 h-8 flex items-center justify-center text-white opacity-70 hover:opacity-100 transition-all">
                <X className="w-5 h-5" />
              </button>
            </div>
            <iframe src="/ai-pipeline.html" className="flex-1 w-full border-none" title="AI Pipeline Documentation" />
          </div>
        </div>
      )}
    </>
  );
}
