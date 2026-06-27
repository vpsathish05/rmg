"use client";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useRmgPipeline, useRmgExtensions, useRmgEmailRequests, useKbStatus,
  useRmgRecommendations, useRecCacheStatus,
  type PipelineProject, type PipelineRole, type RmgCandidate, type KbProof,
} from "@/lib/hooks";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Search, Sparkles, Loader2, AlertTriangle, Database, CheckCircle2,
  Mail, TrendingUp, Calendar, Zap, Users, RefreshCw, Clock, ChevronDown, ChevronRight,
} from "lucide-react";

type TabType = "pipeline" | "extensions" | "changes";

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

// ── Priority badge ─────────────────────────────────────────────────────────
const PRIORITY_STYLE: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  Gold:   { bg: "#FEF9C3", text: "#92400E", border: "#FDE68A", dot: "#D97706" },
  Silver: { bg: "#F1F5F9", text: "#475569", border: "#CBD5E1", dot: "#94A3B8" },
  Bronze: { bg: "#FEF3C7", text: "#78350F", border: "#FCD34D", dot: "#B45309" },
  Other:  { bg: "#F1F5F9", text: "#64748B", border: "#D9D9D9", dot: "#94A3B8" },
};

function PriorityBadge({ value }: { value: string | null }) {
  const s = PRIORITY_STYLE[value ?? "Other"] ?? PRIORITY_STYLE.Other;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide border"
      style={{ background: s.bg, color: s.text, borderColor: s.border }}
    >
      <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: s.dot }} />
      {value ?? "—"}
    </span>
  );
}

function KbProofChip({ proof }: { proof: KbProof }) {
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-semibold"
      style={{ border: "1px solid #C5B8EF", color: "#3411A3", background: "#EEE9F9" }}
    >
      <Database className="w-2.5 h-2.5 shrink-0" />
      {proof.project_id} · {proof.coe ?? "—"} · {Math.round(proof.similarity * 100)}%
    </span>
  );
}

// ── Candidate card ─────────────────────────────────────────────────────────
const SCORE_DIMS = [
  { key: "skill_score", label: "Skill", color: "#3411A3" },
  { key: "comp_score",  label: "Comp",  color: "#FF6196" },
  { key: "avail_score", label: "Avail", color: "#16978E" },
  { key: "prod_score",  label: "Prod",  color: "#A16BDB" },
] as const;

function CandidateCard({ candidate, rank, category }: {
  candidate: RmgCandidate;
  rank: number;
  category: "Available" | "BestMatch";
}) {
  const [showRationale, setShowRationale] = useState(false);
  const isAvail = category === "Available";
  const score = Math.round(candidate.total_score * 100);
  const accentColor = isAvail ? "#16978E" : "#3411A3";
  const bgTint = isAvail ? "#EDFAF9" : "#EEE9F9";

  return (
    <div
      className="rounded-xl bg-white overflow-hidden"
      style={{
        border: "1px solid",
        borderColor: isAvail ? "#A7E3DF" : "#C5B8EF",
        borderLeft: `4px solid ${accentColor}`,
        boxShadow: "0 1px 3px rgba(25,16,91,0.06)",
      }}
    >
      <div className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
              style={{ background: bgTint, color: accentColor, border: `1.5px solid ${accentColor}40` }}
            >
              {rank}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-[#19105B] leading-tight truncate">
                {candidate.job_name ?? candidate.employee_id}
              </p>
              <p className="text-xs text-[#64748B] mt-0.5 leading-snug">
                {[candidate.canonical_role, candidate.location, (candidate.department_name ?? "").split(" ")[0]]
                  .filter(Boolean).join(" · ")}
              </p>
            </div>
          </div>
          <div className="text-right shrink-0">
            <p className="text-2xl font-bold tabular-nums leading-none" style={{ color: accentColor }}>
              {score}%
            </p>
            <p className="text-[10px] text-[#94A3B8] mt-1 leading-none">
              {Math.round(candidate.available_pct)}% free
            </p>
          </div>
        </div>

        <div className="w-full h-1.5 bg-[#F2F2F2] rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-300" style={{ width: `${score}%`, background: accentColor }} />
        </div>

        <div className="grid grid-cols-4 gap-2 pt-0.5">
          {SCORE_DIMS.map(({ key, label, color }) => {
            const val = candidate[key] as number | null;
            if (val == null) return null;
            const pct = Math.round(val * 100);
            return (
              <div key={key} className="flex flex-col items-center gap-1">
                <div className="w-full h-1 bg-[#F2F2F2] rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                </div>
                <p className="text-[10px] font-semibold tabular-nums" style={{ color }}>{pct}</p>
                <p className="text-[9px] text-[#94A3B8] uppercase tracking-wider leading-none">{label}</p>
              </div>
            );
          })}
        </div>

        {candidate.kb_proof?.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-0.5">
            {candidate.kb_proof.map((p, i) => <KbProofChip key={i} proof={p} />)}
          </div>
        )}

        {candidate.rationale && (
          <div>
            <button
              onClick={() => setShowRationale(!showRationale)}
              className="flex items-center gap-1.5 text-xs font-medium"
              style={{ color: "#3411A3" }}
            >
              <Sparkles className="w-3 h-3" />
              {showRationale ? "Hide" : "Show"} AI rationale
            </button>
            {showRationale && (
              <p
                className="text-xs text-[#64748B] mt-2 leading-relaxed rounded-lg px-3 py-2"
                style={{ background: "#F5F5F5", border: "1px solid #D9D9D9" }}
              >
                {candidate.rationale}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Inline recommendations (shown inside expanded role) ────────────────────
function RoleRecommendations({
  entry,
  project,
  role,
  onReload,
  roleKey,
}: {
  entry: CacheEntry | undefined;
  project: PipelineProject;
  role: PipelineRole;
  onReload: () => void;
  roleKey: string;
}) {
  return (
    <div className="px-6 pb-5 pt-3 space-y-4" style={{ background: "#F7F7FA" }}>
      {/* Role meta strip */}
      <div className="flex flex-wrap items-center gap-2 pb-3" style={{ borderBottom: "1px solid #EBEBEB" }}>
        {entry?.coe && (
          <span
            className="text-xs font-bold px-2.5 py-0.5 rounded-full"
            style={{ background: "#EEE9F9", color: "#3411A3", border: "1px solid #C5B8EF" }}
          >
            {entry.coe}
          </span>
        )}
        {role.allocation_pct != null && (
          <span className="text-xs text-[#64748B] bg-white px-2 py-0.5 rounded-full border border-[#D9D9D9]">
            {role.allocation_pct}% alloc
          </span>
        )}
        {role.duration_weeks != null && (
          <span className="text-xs text-[#64748B] bg-white px-2 py-0.5 rounded-full border border-[#D9D9D9]">
            {role.duration_weeks}w
          </span>
        )}
        {project.likely_start_date && (
          <span className="text-xs text-[#64748B] flex items-center gap-1 bg-white px-2 py-0.5 rounded-full border border-[#D9D9D9]">
            <Calendar className="w-3 h-3" />
            {new Date(project.likely_start_date).toLocaleDateString("en-GB", {
              day: "numeric", month: "short", year: "numeric",
            })}
          </span>
        )}
        {project.em_name && (
          <span className="text-xs text-[#64748B]">EM: {project.em_name}</span>
        )}
        {entry?.status === "error" && (
          <button
            onClick={onReload}
            className="ml-auto text-xs flex items-center gap-1.5 text-red-500 hover:underline"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        )}
      </div>

      {/* Content */}
      {!entry || entry.status === "loading" ? (
        <div className="flex items-center gap-3 py-8 justify-center text-[#64748B]">
          <Loader2 className="w-6 h-6 animate-spin" style={{ color: "#3411A3" }} />
          <div>
            <p className="text-sm font-medium">Scoring candidates…</p>
            <p className="text-xs text-[#94A3B8] mt-0.5">
              COE: {entry?.coe ?? "detecting…"}
            </p>
          </div>
        </div>
      ) : entry.status === "error" ? (
        <div
          className="flex items-start gap-3 p-4 rounded-xl"
          style={{ background: "#FEF2F2", border: "1px solid #FECACA" }}
        >
          <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">Could not load recommendations</p>
            <p className="text-xs text-red-600 mt-0.5">
              {!entry.coe
                ? "COE could not be detected. Check canonical_roles in pipeline data."
                : "Scoring failed — please retry."}
            </p>
          </div>
        </div>
      ) : entry.data ? (
        <>
          {/* Summary row */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
              style={{ background: "#EDFAF9", color: "#16978E", border: "1px solid #A7E3DF" }}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {entry.data.available.length} Available
            </span>
            <span
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
              style={{ background: "#EEE9F9", color: "#3411A3", border: "1px solid #C5B8EF" }}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {entry.data.best_match.length} Best Match
            </span>
            <span className="text-xs text-[#94A3B8]">{entry.data.total_evaluated} evaluated</span>
            {entry.data.kb_active && (
              <span
                className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ml-auto"
                style={{ background: "#EEE9F9", color: "#3411A3", border: "1px solid #C5B8EF" }}
              >
                <Database className="w-3 h-3" /> KB active
              </span>
            )}
          </div>

          {/* Available candidates */}
          {entry.data.available.length > 0 && (
            <section>
              <div
                className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg"
                style={{ background: "#EDFAF9", border: "1px solid #A7E3DF" }}
              >
                <CheckCircle2 className="w-3.5 h-3.5" style={{ color: "#16978E" }} />
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "#16978E" }}>
                  Available — {entry.data.available.length} candidate{entry.data.available.length !== 1 ? "s" : ""}
                </span>
                <span className="text-[10px] ml-1" style={{ color: "#16978E", opacity: 0.65 }}>
                  exact role · sufficient capacity
                </span>
              </div>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                {entry.data.available.map((c, i) => (
                  <CandidateCard key={c.employee_id} candidate={c} rank={i + 1} category="Available" />
                ))}
              </div>
            </section>
          )}

          {/* Best Match candidates */}
          {entry.data.best_match.length > 0 && (
            <section>
              <div
                className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg"
                style={{ background: "#EEE9F9", border: "1px solid #C5B8EF" }}
              >
                <Sparkles className="w-3.5 h-3.5" style={{ color: "#3411A3" }} />
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "#3411A3" }}>
                  Best Match — {entry.data.best_match.length} candidate{entry.data.best_match.length !== 1 ? "s" : ""}
                </span>
                <span className="text-[10px] ml-1" style={{ color: "#3411A3", opacity: 0.65 }}>
                  AI-scored · may need negotiation
                </span>
              </div>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                {entry.data.best_match.map((c, i) => (
                  <CandidateCard key={c.employee_id} candidate={c} rank={i + 1} category="BestMatch" />
                ))}
              </div>
            </section>
          )}

          {/* No resource */}
          {entry.data.no_resource && (
            <div
              className="flex items-start gap-3 p-4 rounded-xl"
              style={{ background: "#FFFBEB", border: "1px solid #FDE68A" }}
            >
              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-amber-900 mb-1">No Resource to Recommend</p>
                <p className="text-xs text-amber-700 leading-relaxed">{entry.data.hire_signal}</p>
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

// ── Pipeline accordion ─────────────────────────────────────────────────────
function PipelineAccordion({
  projects,
  recCache,
  expandedClients,
  expandedRoleKey,
  onToggleClient,
  onToggleRole,
  onReloadRole,
  onExpandAll,
  onCollapseAll,
  search,
  setSearch,
  showNROnly,
  setShowNROnly,
}: {
  projects: PipelineProject[];
  recCache: Record<string, CacheEntry>;
  expandedClients: Set<string>;
  expandedRoleKey: string | null;
  onToggleClient: (name: string) => void;
  onToggleRole: (key: string, project: PipelineProject, role: PipelineRole) => void;
  onReloadRole: (key: string, project: PipelineProject, role: PipelineRole) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  search: string;
  setSearch: (s: string) => void;
  showNROnly: boolean;
  setShowNROnly: (v: boolean) => void;
}) {
  const nrCount = projects.reduce(
    (n, p) => n + p.roles.filter(r => r.status === "Not Resourced").length, 0
  );
  const anyOpen = expandedClients.size > 0;

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
      {/* Search + filter bar */}
      <div className="px-6 py-3 border-b bg-white shrink-0">
        <div className="flex items-center gap-2">
          <div className="relative flex-1 max-w-xs">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8] pointer-events-none" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search client…"
              className="w-full pl-8 pr-3 py-1.5 text-sm bg-[#F5F5F5] border border-[#D9D9D9] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#3411A3]/30 focus:border-[#3411A3] transition-all"
            />
          </div>
          <button
            onClick={() => setShowNROnly(!showNROnly)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all shrink-0"
            style={
              showNROnly
                ? { background: "#FEF2F2", borderColor: "#FECACA", color: "#DC2626" }
                : { background: "#F5F5F5", borderColor: "#D9D9D9", color: "#64748B" }
            }
          >
            Not Resourced only
          </button>

          {/* Divider */}
          <div className="w-px h-5 bg-[#E8E8E8] shrink-0" />

          {/* Expand / Collapse All */}
          <button
            onClick={anyOpen ? onCollapseAll : onExpandAll}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all shrink-0 flex items-center gap-1.5"
            style={{ background: "#F5F5F5", borderColor: "#D9D9D9", color: "#64748B" }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.borderColor = "#3411A3";
              (e.currentTarget as HTMLElement).style.color = "#3411A3";
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.borderColor = "#D9D9D9";
              (e.currentTarget as HTMLElement).style.color = "#64748B";
            }}
          >
            {anyOpen
              ? <><ChevronDown className="w-3 h-3" /> Collapse All</>
              : <><ChevronRight className="w-3 h-3" /> Expand All</>
            }
          </button>

          <span className="text-xs text-[#94A3B8] ml-auto tabular-nums shrink-0">
            {nrCount} open role{nrCount !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Accordion list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {projects.length === 0 ? (
          <div className="flex items-center justify-center py-20 text-sm text-[#94A3B8]">
            No projects found
          </div>
        ) : (
          projects.map(project => {
            const isOpen = expandedClients.has(project.client_name);
            const nrRoles = project.roles.filter(r => r.status === "Not Resourced");

            return (
              <div
                key={project.client_name}
                className="bg-white rounded-xl overflow-hidden"
                style={{ border: "1px solid #E8E8E8", boxShadow: "0 1px 3px rgba(25,16,91,0.04)" }}
              >
                {/* Client header — click to expand */}
                <button
                  onClick={() => onToggleClient(project.client_name)}
                  className="w-full flex items-center gap-2.5 px-4 py-3 text-left transition-colors hover:bg-[#FAFAFA]"
                  style={{ borderBottom: isOpen ? "1px solid #F2F2F2" : "none" }}
                >
                  {isOpen
                    ? <ChevronDown className="w-4 h-4 shrink-0 text-[#94A3B8]" />
                    : <ChevronRight className="w-4 h-4 shrink-0 text-[#94A3B8]" />
                  }
                  <PriorityBadge value={project.client_priority} />
                  <span className="text-sm font-bold text-[#19105B] flex-1 truncate">
                    {project.client_name}
                  </span>
                  {project.probability_weight != null && (
                    <span className="text-[11px] font-medium tabular-nums text-[#64748B]">
                      {Math.round(project.probability_weight * 100)}%
                    </span>
                  )}
                  {nrRoles.length > 0 && (
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                      style={{ background: "#FEF2F2", color: "#DC2626", border: "1px solid #FECACA" }}
                    >
                      {nrRoles.length} open
                    </span>
                  )}
                </button>

                {/* Roles accordion */}
                {isOpen && (
                  <div>
                    {project.roles.map(role => {
                      const roleKey = `${project.client_name}::${role.id}`;
                      const isRoleOpen = expandedRoleKey === roleKey;
                      const entry = recCache[roleKey];
                      const isNR = role.status === "Not Resourced";

                      return (
                        <div
                          key={role.id}
                          style={{ borderTop: "1px solid #F2F2F2" }}
                        >
                          {/* Role header row — click to expand recommendations */}
                          <button
                            onClick={() => onToggleRole(roleKey, project, role)}
                            className="w-full flex items-center gap-3 px-5 py-3 text-left transition-all"
                            style={{
                              background: isRoleOpen ? "#F7F7FA" : "transparent",
                              borderLeft: `3px solid ${isRoleOpen ? "#3411A3" : "transparent"}`,
                            }}
                            onMouseEnter={e => {
                              if (!isRoleOpen)
                                (e.currentTarget as HTMLElement).style.background = "#FAFAFA";
                            }}
                            onMouseLeave={e => {
                              if (!isRoleOpen)
                                (e.currentTarget as HTMLElement).style.background = "transparent";
                            }}
                          >
                            {/* Status badge */}
                            {entry?.status === "loading" ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" style={{ color: "#3411A3" }} />
                            ) : isNR ? (
                              <span
                                className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                                style={{ background: "#FEF2F2", color: "#DC2626", border: "1px solid #FECACA" }}
                              >
                                Not Resourced
                              </span>
                            ) : (
                              <span
                                className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                                style={{ background: "#EDFAF9", color: "#16978E", border: "1px solid #A7E3DF" }}
                              >
                                Resourced
                              </span>
                            )}

                            {/* Role name + meta */}
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm truncate leading-tight ${isNR ? "font-semibold text-[#19105B]" : "font-medium text-[#64748B]"}`}>
                                {role.role_code_raw ?? "—"}
                              </p>
                              {(role.allocation_pct != null || role.duration_weeks != null) && (
                                <p className="text-[10px] text-[#94A3B8] mt-0.5">
                                  {[
                                    role.allocation_pct != null ? `${role.allocation_pct}% alloc` : null,
                                    role.duration_weeks != null ? `${role.duration_weeks}w` : null,
                                  ].filter(Boolean).join(" · ")}
                                </p>
                              )}
                            </div>

                            {/* Done tick for NR roles */}
                            {entry?.status === "done" && isNR && (
                              <CheckCircle2 className="w-4 h-4 shrink-0" style={{ color: "#16978E" }} />
                            )}

                            {/* Expand chevron */}
                            {isNR && (
                              isRoleOpen
                                ? <ChevronDown className="w-3.5 h-3.5 shrink-0 text-[#3411A3]" />
                                : <ChevronRight className="w-3.5 h-3.5 shrink-0 text-[#94A3B8]" />
                            )}
                          </button>

                          {/* Inline recommendations */}
                          {isRoleOpen && (
                            <RoleRecommendations
                              entry={entry}
                              project={project}
                              role={role}
                              roleKey={roleKey}
                              onReload={() => onReloadRole(roleKey, project, role)}
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ── Extensions view ────────────────────────────────────────────────────────
function ExtensionsView() {
  const { data, isLoading } = useRmgExtensions();
  const extensions = data?.allocation_extensions ?? [];
  const emailExts = data?.email_extensions ?? [];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <section>
        <h2 className="text-sm font-semibold text-[#19105B] mb-3 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" style={{ color: "#A16BDB" }} />
          Allocation Extensions ({extensions.length})
          <span className="text-[10px] text-[#94A3B8] font-normal">— allocation end exceeds project end</span>
        </h2>
        {isLoading ? (
          <div className="text-xs text-[#94A3B8] flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading…
          </div>
        ) : extensions.length === 0 ? (
          <div className="text-xs text-[#94A3B8] py-6 text-center">No extended allocations found</div>
        ) : (
          <div className="overflow-x-auto rounded-xl" style={{ border: "1px solid #EEE9F9" }}>
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: "#EEE9F9", color: "#19105B" }}>
                  {["Project", "Client", "COE", "Project End", "Alloc End", "Extended By", "HC"].map(h => (
                    <th key={h} className="px-3 py-2 text-left font-bold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {extensions.slice(0, 50).map((e, i) => (
                  <tr key={e.project_id}
                    style={{ background: i % 2 === 0 ? "#fff" : "#FAFAFA", borderTop: "1px solid #F2F2F2" }}>
                    <td className="px-3 py-2 font-mono text-[10px]">{e.project_id}</td>
                    <td className="px-3 py-2">{e.client_id}</td>
                    <td className="px-3 py-2 text-[#64748B]">{e.proposition_coe ?? "—"}</td>
                    <td className="px-3 py-2 tabular-nums">
                      {e.project_end_date ? new Date(e.project_end_date).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums">
                      {e.max_alloc_end_date ? new Date(e.max_alloc_end_date).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums font-bold" style={{ color: "#A16BDB" }}>+{e.days_extended}d</td>
                    <td className="px-3 py-2 tabular-nums">{e.headcount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {emailExts.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-[#19105B] mb-3 flex items-center gap-2">
            <Mail className="w-4 h-4 text-[#3411A3]" />
            Email Extension Requests ({emailExts.length})
          </h2>
          <div className="space-y-2">
            {emailExts.map(e => (
              <div key={e.id}
                className="border border-[#D9D9D9] rounded-lg p-3 text-xs flex items-center gap-3"
                style={{ background: "#FAFAFA" }}>
                <span className="text-[#64748B]">{e.source_email}</span>
                <span className="text-[#94A3B8]">
                  {e.received_at ? new Date(e.received_at).toLocaleDateString() : "—"}
                </span>
                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-[#EEE9F9] text-[#3411A3]">{e.status}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ── Changes view ───────────────────────────────────────────────────────────
function ChangesView() {
  const { data: requests = [], isLoading } = useRmgEmailRequests();
  const changes = requests.filter(r => r.request_type === "CHANGE" || r.request_type === "NEW");

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h2 className="text-sm font-semibold text-[#19105B] mb-4 flex items-center gap-2">
        <Mail className="w-4 h-4 text-[#3411A3]" />
        Change Requests ({changes.length})
      </h2>
      {isLoading ? (
        <div className="text-xs text-[#94A3B8] flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading…
        </div>
      ) : changes.length === 0 ? (
        <div className="text-center py-16 text-[#94A3B8]">
          <Mail className="w-8 h-8 mx-auto mb-3 opacity-30" />
          <p className="text-sm font-medium mb-1">No change requests yet</p>
          <p className="text-xs max-w-xs mx-auto leading-relaxed">
            Send email to{" "}
            <span className="text-[#64748B] font-mono">sathishkumar@jmangroup.com</span>{" "}
            with subject "Resource Request"
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {changes.map(r => (
            <div key={r.id}
              className="border border-[#D9D9D9] rounded-lg p-3 text-xs space-y-2 hover:bg-[#F5F5F5]">
              <div className="flex items-center gap-3">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  r.request_type === "CHANGE" ? "bg-orange-100 text-orange-700" : "bg-purple-100 text-purple-700"
                }`}>
                  {r.request_type}
                </span>
                <span className="text-[#64748B]">{r.source_email}</span>
                <span className="text-[#94A3B8] ml-auto">
                  {r.received_at ? new Date(r.received_at).toLocaleDateString() : "—"}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#F2F2F2] text-[#64748B]">{r.status}</span>
              </div>
              {r.parsed_json && (
                <pre className="text-[9px] text-[#64748B] bg-[#F5F5F5] rounded px-2 py-1.5 overflow-x-auto font-mono leading-relaxed">
                  {JSON.stringify(r.parsed_json, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
const TABS: { id: TabType; label: string }[] = [
  { id: "pipeline",   label: "Pipeline" },
  { id: "extensions", label: "Extensions" },
  { id: "changes",    label: "Changes" },
];

export default function RmgEnginePage() {
  const [tab, setTab] = useState<TabType>("pipeline");
  const [search, setSearch] = useState("");
  const [showNROnly, setShowNROnly] = useState(false);
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

  const buildKb = useMutation({
    mutationFn: () => api.post("/api/rmg/kb/build"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["kb-status"] }),
  });

  const refreshRecs = useMutation({
    mutationFn: () => api.post("/api/rmg/recommendations/refresh"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rec-cache-status"] }),
  });

  const projects = useMemo(() => {
    let list = rawProjects;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(p => p.client_name?.toLowerCase().includes(q));
    }
    if (showNROnly) {
      list = list.filter(p => p.roles.some(r => r.status === "Not Resourced"));
    }
    return list;
  }, [rawProjects, search, showNROnly]);

  const loadRole = useCallback(
    async (key: string, _project: PipelineProject, role: PipelineRole) => {
      if (loadingRef.current.has(key)) return;
      loadingRef.current.add(key);
      setRecCache(prev => ({ ...prev, [key]: { status: "loading" } }));

      try {
        const params = new URLSearchParams();
        (role.canonical_roles ?? []).forEach(r => params.append("canonical_roles", r));
        const { data: coeData } = await api.get(`/api/rmg/auto-coe?${params.toString()}`);
        const coe: string | null = coeData.coe;

        if (!coe) {
          setRecCache(prev => ({ ...prev, [key]: { status: "error" } }));
          loadingRef.current.delete(key);
          return;
        }

        const { data } = await api.post("/api/rmg/recommend-role", {
          role_code: role.role_code_raw ?? "Unknown",
          canonical_roles: role.canonical_roles,
          coe,
          allocation_pct: role.allocation_pct ?? 100,
          required_skills: role.required_skills,
          with_rationale: false,
          with_kb_proof: true,
        });

        setRecCache(prev => ({ ...prev, [key]: { status: "done", coe, data } }));
      } catch {
        setRecCache(prev => ({ ...prev, [key]: { status: "error" } }));
        loadingRef.current.delete(key);
      }
    },
    []
  );

  // Hydrate cache from server pre-computed recommendations
  useEffect(() => {
    if (!serverRecs || !rawProjects.length) return;
    const toAdd: Record<string, CacheEntry> = {};
    rawProjects.forEach(p =>
      p.roles.forEach(r => {
        const key = `${p.client_name}::${r.id}`;
        const cached = serverRecs[String(r.id)];
        if (cached && !loadingRef.current.has(key)) {
          loadingRef.current.add(key);
          toAdd[key] = {
            status: "done",
            coe: cached.coe ?? undefined,
            data: {
              available:       cached.available,
              best_match:      cached.best_match,
              no_resource:     cached.no_resource,
              hire_signal:     cached.hire_signal,
              kb_active:       cached.kb_active,
              total_evaluated: cached.total_evaluated,
            },
          };
        }
      })
    );
    if (Object.keys(toAdd).length) {
      setRecCache(prev => ({ ...toAdd, ...prev }));
    }
  }, [serverRecs, rawProjects]);

  // Auto-expand FIRST NR client only + auto-open its first NR role + background pre-load
  useEffect(() => {
    if (!rawProjects.length) return;

    if (!initialExpandedRef.current) {
      initialExpandedRef.current = true;

      // Only open the first client that has NR roles
      const firstNRClient = rawProjects.find(p => p.roles.some(r => r.status === "Not Resourced"));
      if (firstNRClient) {
        setExpandedClients(new Set([firstNRClient.client_name]));
        const firstNRRole = firstNRClient.roles.find(r => r.status === "Not Resourced");
        if (firstNRRole) {
          const key = `${firstNRClient.client_name}::${firstNRRole.id}`;
          setExpandedRoleKey(key);
          loadRole(key, firstNRClient, firstNRRole);
        }
      }
    }

    // Background pre-load all NR roles
    rawProjects.forEach(p =>
      p.roles.filter(r => r.status === "Not Resourced").forEach(r => {
        const key = `${p.client_name}::${r.id}`;
        loadRole(key, p, r);
      })
    );
  }, [rawProjects, loadRole]);

  // Single-open: opening a project closes all others
  const handleToggleClient = useCallback((name: string) => {
    setExpandedClients(prev => {
      if (prev.has(name)) {
        // Clicking the open one → close it
        return new Set<string>();
      }
      // Clicking a closed one → close all others, open only this one
      return new Set([name]);
    });
    // Also close any open role that belonged to a different project
    setExpandedRoleKey(prev => {
      if (prev && !prev.startsWith(`${name}::`)) return null;
      return prev;
    });
  }, []);

  const handleExpandAll = useCallback(() => {
    setExpandedClients(new Set(rawProjects.map(p => p.client_name)));
  }, [rawProjects]);

  const handleCollapseAll = useCallback(() => {
    setExpandedClients(new Set());
    setExpandedRoleKey(null);
  }, []);

  const handleToggleRole = useCallback(
    (key: string, project: PipelineProject, role: PipelineRole) => {
      setExpandedRoleKey(prev => {
        if (prev === key) return null;
        loadRole(key, project, role);
        return key;
      });
    },
    [loadRole]
  );

  const handleReloadRole = useCallback(
    (key: string, project: PipelineProject, role: PipelineRole) => {
      loadingRef.current.delete(key);
      loadRole(key, project, role);
    },
    [loadRole]
  );

  const lastScoredLabel = useMemo(() => {
    const ts = cacheStatus?.last_computed_at;
    if (!ts) return null;
    const d = new Date(ts);
    const diffMin = Math.round((Date.now() - d.getTime()) / 60000);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  }, [cacheStatus?.last_computed_at]);

  return (
    <>
      {/* Top bar — tabs + actions only */}
      <div className="flex items-center gap-2 px-6 py-3 border-b bg-white shrink-0">
        {/* Tabs */}
        <div className="flex items-center gap-1">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className="px-4 py-1.5 text-sm font-semibold rounded-lg transition-all"
              style={
                tab === id
                  ? { background: "#19105B", color: "#fff", boxShadow: "0 1px 3px rgba(25,16,91,0.2)" }
                  : { color: "#64748B" }
              }
              onMouseEnter={e => {
                if (tab !== id)
                  (e.currentTarget as HTMLElement).style.background = "#F2F2F2";
              }}
              onMouseLeave={e => {
                if (tab !== id)
                  (e.currentTarget as HTMLElement).style.background = "transparent";
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        {/* Action row */}
        <div className="flex items-center gap-3">
          {lastScoredLabel && !cacheStatus?.is_running && (
            <span className="text-[10px] text-[#94A3B8] flex items-center gap-1">
              <Clock className="w-3 h-3" /> scored {lastScoredLabel}
            </span>
          )}
          {cacheStatus?.is_running && (
            <span className="text-[10px] text-[#3411A3] flex items-center gap-1 animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" /> Scoring…
            </span>
          )}
          {kbStatus && (
            <span className="text-[10px] text-[#64748B] flex items-center gap-1.5">
              <Database className="w-3 h-3" /> {kbStatus.embeddings} KB
            </span>
          )}
          <Button
            size="sm"
            variant="outline"
            className="text-xs h-7 gap-1"
            onClick={() => refreshRecs.mutate()}
            disabled={refreshRecs.isPending || cacheStatus?.is_running}
          >
            {refreshRecs.isPending || cacheStatus?.is_running
              ? <Loader2 className="w-3 h-3 animate-spin" />
              : <RefreshCw className="w-3 h-3" />}
            Refresh Scores
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-xs h-7 gap-1"
            onClick={() => buildKb.mutate()}
            disabled={buildKb.isPending}
          >
            {buildKb.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
            Build KB
          </Button>
        </div>
      </div>

      {/* Pipeline accordion */}
      {tab === "pipeline" && (
        pipelinesLoading ? (
          <div className="flex-1 flex items-center justify-center gap-2 text-sm text-[#94A3B8]">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading pipeline…
          </div>
        ) : (
          <PipelineAccordion
            projects={projects}
            recCache={recCache}
            expandedClients={expandedClients}
            expandedRoleKey={expandedRoleKey}
            onToggleClient={handleToggleClient}
            onToggleRole={handleToggleRole}
            onReloadRole={handleReloadRole}
            onExpandAll={handleExpandAll}
            onCollapseAll={handleCollapseAll}
            search={search}
            setSearch={setSearch}
            showNROnly={showNROnly}
            setShowNROnly={setShowNROnly}
          />
        )
      )}

      {tab === "extensions" && <ExtensionsView />}
      {tab === "changes" && <ChangesView />}
    </>
  );
}
