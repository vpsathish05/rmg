"use client";
import { useState, useMemo } from "react";
import Link from "next/link";
import { useForecast, useForecastOutlook, type OutlookMonth } from "@/lib/hooks";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Sparkles, TrendingUp, Target, BarChart3 } from "lucide-react";

// ── Priority / SOW styles ───────────────────────────────────────────────────
const PRIORITY_STYLE: Record<string, string> = {
  High:   "bg-red-50 text-red-700 border-red-200",
  Medium: "bg-amber-50 text-amber-700 border-amber-200",
  Low:    "bg-muted text-muted-foreground border-border",
};

const SOW_STYLE: Record<string, string> = {
  true:  "bg-emerald-50 text-emerald-700 border-emerald-200",
  false: "bg-muted text-muted-foreground border-border",
};

function probColor(p: number | null): string {
  if (!p) return "#94A3B8";
  if (p >= 0.9) return "#059669";
  if (p >= 0.7) return "#3411A3";
  if (p >= 0.5) return "#D97706";
  return "#94A3B8";
}

// ── KPI tile ────────────────────────────────────────────────────────────────
function ForecastKpi({
  label,
  value,
  sub,
  accent,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent: string;
  icon: React.ElementType;
}) {
  return (
    <div
      className="bg-card rounded-xl p-5 flex flex-col gap-1.5"
      style={{
        boxShadow: "0 1px 4px rgba(10,22,40,0.07)",
        borderTop: `3px solid ${accent}`,
      }}
    >
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          {label}
        </p>
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center"
          style={{ background: `${accent}18` }}
        >
          <Icon className="w-3.5 h-3.5" style={{ color: accent }} />
        </div>
      </div>
      <p className="text-4xl font-bold tabular-nums leading-none" style={{ color: accent }}>
        {value}
      </p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

// ── 6-month outlook chart ───────────────────────────────────────────────────
const TOP_ROLES_N = 5;
const ROLE_COLORS = ["#3411A3", "#26D4F0", "#FF6196", "#A16BDB", "#71EAE1", "#16978E"];

function OutlookChart({ months }: { months: OutlookMonth[] }) {
  const allRoles = useMemo(() => {
    const totals: Record<string, number> = {};
    months.forEach((m) => m.roles.forEach((r) => {
      totals[r.role] = (totals[r.role] ?? 0) + r.total_fte;
    }));
    return Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, TOP_ROLES_N).map(([r]) => r);
  }, [months]);

  const maxFte = useMemo(() => Math.max(...months.map((m) => m.total_fte), 1), [months]);

  if (months.length === 0) {
    return (
      <div className="py-20 text-center text-sm text-muted-foreground">
        No pipeline starts in the next 6 months.
      </div>
    );
  }

  const BAR_H = 180;
  const BAR_W = 56;
  const GAP   = 28;
  const LABEL_H = 36;
  const svgW = months.length * (BAR_W + GAP) + GAP;
  const svgH = BAR_H + LABEL_H + 24;

  return (
    <div>
      {/* Legend */}
      <div className="flex flex-wrap gap-5 mb-6">
        {allRoles.map((role, i) => (
          <div key={role} className="flex items-center gap-2 text-xs text-[#64748B]">
            <span
              className="w-3 h-3 rounded-sm inline-block"
              style={{ background: ROLE_COLORS[i] }}
            />
            {role}
          </div>
        ))}
        <div className="flex items-center gap-2 text-xs text-[#94A3B8]">
          <span className="w-3 h-3 rounded-sm inline-block" style={{ background: "#D9D9D9" }} />
          Other
        </div>
      </div>

      <div
        className="rounded-xl p-6 overflow-x-auto"
        style={{ background: "#F5F5F5", border: "1px solid #D9D9D9" }}
      >
        <svg width={svgW} height={svgH} style={{ overflow: "visible" }}>
          {/* Horizontal grid lines */}
          {[0.25, 0.5, 0.75, 1].map((f) => (
            <line
              key={f}
              x1={0} y1={BAR_H * (1 - f)} x2={svgW} y2={BAR_H * (1 - f)}
              stroke="#D9D9D9" strokeWidth={1} strokeDasharray="3 3"
            />
          ))}

          {months.map((m, mi) => {
            const x = GAP + mi * (BAR_W + GAP);
            let yOffset = BAR_H;
            const slices: { role: string; h: number; color: string; isFirst: boolean }[] = [];

            const roleMap: Record<string, number> = {};
            m.roles.forEach((r) => { roleMap[r.role] = r.total_fte; });
            let otherFte = m.total_fte;
            allRoles.forEach((role, ri) => {
              const fte = roleMap[role] ?? 0;
              if (fte > 0) {
                slices.push({ role, h: Math.round((fte / maxFte) * BAR_H), color: ROLE_COLORS[ri], isFirst: false });
                otherFte -= fte;
              }
            });
            if (otherFte > 0.05) {
              slices.push({ role: "Other", h: Math.round((otherFte / maxFte) * BAR_H), color: "#CBD5E1", isFirst: false });
            }
            slices.reverse();
            if (slices.length > 0) slices[0] = { ...slices[0], isFirst: true };

            return (
              <g key={m.month}>
                {slices.map((s) => {
                  yOffset -= s.h;
                  const y = yOffset;
                  return (
                    <rect
                      key={s.role}
                      x={x} y={y} width={BAR_W} height={s.h}
                      fill={s.color}
                      rx={s.isFirst ? 4 : 0}
                      style={{ transition: "height 0.4s ease" }}
                    />
                  );
                })}
                {/* FTE label above bar */}
                <text x={x + BAR_W / 2} y={yOffset - 7} textAnchor="middle"
                  fontSize={11} fontWeight="600" fill="#475569">
                  {m.weighted_fte.toFixed(1)}
                </text>
                {/* Month label */}
                <text x={x + BAR_W / 2} y={BAR_H + LABEL_H - 14} textAnchor="middle"
                  fontSize={12} fontWeight="500" fill="#475569">
                  {m.month.slice(5)}
                </text>
                <text x={x + BAR_W / 2} y={BAR_H + LABEL_H + 4} textAnchor="middle"
                  fontSize={10} fill="#CBD5E1">
                  {m.month.slice(0, 4)}
                </text>
              </g>
            );
          })}

          {/* Baseline */}
          <line x1={0} y1={BAR_H} x2={svgW} y2={BAR_H} stroke="#CBD5E1" strokeWidth={1.5} />
        </svg>
      </div>

      {/* Summary table */}
      <div className="mt-6 rounded-xl border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow style={{ background: "#F5F5F5" }}>
              <TableHead className="text-xs font-semibold text-[#64748B]">Month</TableHead>
              <TableHead className="text-xs font-semibold text-[#64748B]">Top Role</TableHead>
              <TableHead className="text-right text-xs font-semibold text-[#64748B]">Requests</TableHead>
              <TableHead className="text-right text-xs font-semibold text-[#64748B]">Total FTE</TableHead>
              <TableHead className="text-right text-xs font-semibold text-[#64748B]">Weighted FTE</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {months.map((m, i) => (
              <TableRow
                key={m.month}
                style={{ background: i % 2 === 0 ? "#fff" : "#F5F5F5" }}
                className="hover:bg-blue-50/30 transition-colors"
              >
                <TableCell className="font-mono text-sm font-medium">{m.month}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {m.roles[0]?.role ?? "—"}
                  {m.roles.length > 1 && (
                    <span className="text-xs text-muted-foreground/60"> +{m.roles.length - 1}</span>
                  )}
                </TableCell>
                <TableCell className="text-right tabular-nums text-sm">
                  {m.roles.reduce((s, r) => s + r.request_count, 0)}
                </TableCell>
                <TableCell
                  className="text-right tabular-nums text-sm font-bold"
                  style={{ color: "#3411A3" }}
                >
                  {m.total_fte.toFixed(1)}
                </TableCell>
                <TableCell className="text-right tabular-nums text-sm text-muted-foreground">
                  {m.weighted_fte.toFixed(1)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ── Pipeline list ──────────────────────────────────────────────────────────
function PipelineList() {
  const [search, setSearch] = useState("");
  const { data, isLoading, error } = useForecast();

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!search) return data;
    const q = search.toLowerCase();
    return data.filter(
      (r) =>
        (r.client_name ?? "").toLowerCase().includes(q) ||
        (r.role_code_raw ?? "").toLowerCase().includes(q) ||
        (r.solution ?? "").toLowerCase().includes(q) ||
        (r.deal_stage ?? "").toLowerCase().includes(q)
    );
  }, [data, search]);

  const grouped = useMemo(() => {
    const seen = new Set<string>();
    return filtered.map((r) => {
      const isFirst = !seen.has(r.client_name ?? "");
      if (r.client_name) seen.add(r.client_name);
      return { ...r, isFirstInGroup: isFirst };
    });
  }, [filtered]);

  if (isLoading)
    return (
      <div className="py-12 text-sm text-muted-foreground flex items-center gap-2">
        <BarChart3 className="w-4 h-4 animate-pulse" /> Loading pipeline…
      </div>
    );
  if (error)
    return <div className="py-12 text-sm text-destructive">Failed to load pipeline data.</div>;

  return (
    <>
      <div className="mb-5">
        <Input
          placeholder="Search client / role / solution / deal stage…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm bg-card"
        />
      </div>

      <div
        className="rounded-xl border border-border bg-card overflow-hidden overflow-x-auto"
        style={{ boxShadow: "0 1px 4px rgba(10,22,40,0.06)" }}
      >
        <Table>
          <TableHeader>
            <TableRow style={{ background: "#F5F5F5" }}>
              <TableHead className="w-8 text-xs font-semibold text-[#64748B]">#</TableHead>
              <TableHead className="text-xs font-semibold text-[#64748B]">Client</TableHead>
              <TableHead className="text-xs font-semibold text-[#64748B]">Deal Stage</TableHead>
              <TableHead className="text-xs font-semibold text-[#64748B]">Solution</TableHead>
              <TableHead className="text-xs font-semibold text-[#64748B]">Role</TableHead>
              <TableHead className="text-center w-16 text-xs font-semibold text-[#64748B]">%</TableHead>
              <TableHead className="text-center text-xs font-semibold text-[#64748B]">Priority</TableHead>
              <TableHead className="text-center text-xs font-semibold text-[#64748B]">SOW</TableHead>
              <TableHead className="text-right w-24 text-xs font-semibold text-[#64748B]">Probability</TableHead>
              <TableHead className="w-28 text-xs font-semibold text-[#64748B]">Start Date</TableHead>
              <TableHead className="text-center w-16 text-xs font-semibold text-[#64748B]">Weeks</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {grouped.length === 0 && (
              <TableRow>
                <TableCell colSpan={12} className="text-center py-12 text-muted-foreground text-sm">
                  No pipeline requests match your search.
                </TableCell>
              </TableRow>
            )}
            {grouped.map((r, i) => {
              const findUrl = r.role_code_raw
                ? `/recommend?role_code=${encodeURIComponent(r.role_code_raw)}${r.allocation_pct ? `&allocation=${r.allocation_pct}` : ""}${r.duration_weeks ? `&weeks=${r.duration_weeks}` : ""}`
                : null;
              return (
                <TableRow
                  key={r.id}
                  className={`transition-colors ${r.isFirstInGroup && i > 0 ? "border-t-2 border-border" : ""}`}
                  style={{ background: i % 2 === 0 ? "#fff" : "#F5F5F5" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "#EFF6FF")}
                  onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "#F5F5F5")}
                >
                  <TableCell className="text-xs text-muted-foreground tabular-nums">{r.id}</TableCell>
                  <TableCell className="text-sm font-semibold text-[#19105B]">
                    {r.client_name ?? "—"}
                    {r.client_priority && (
                      <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                        ({r.client_priority})
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{r.deal_stage ?? "—"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{r.solution ?? "—"}</TableCell>
                  <TableCell>
                    <span className="text-sm font-mono font-medium">{r.role_code_raw ?? "—"}</span>
                    {r.canonical_roles && r.canonical_roles.length > 0 && (
                      <span className="ml-1 text-xs text-muted-foreground">({r.canonical_roles[0]})</span>
                    )}
                  </TableCell>
                  <TableCell className="text-center tabular-nums text-sm">
                    {r.allocation_pct != null ? `${r.allocation_pct}%` : "—"}
                  </TableCell>
                  <TableCell className="text-center">
                    {r.priority ? (
                      <Badge variant="outline" className={`text-xs ${PRIORITY_STYLE[r.priority] ?? ""}`}>
                        {r.priority}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className={`text-xs ${SOW_STYLE[String(r.sow_signed)]}`}>
                      {r.sow_signed ? "Yes" : "No"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm font-bold">
                    {r.probability_weight != null ? (
                      <span style={{ color: probColor(r.probability_weight) }}>
                        {Math.round(r.probability_weight * 100)}%
                      </span>
                    ) : "—"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{r.likely_start_date ?? "—"}</TableCell>
                  <TableCell className="text-center tabular-nums text-sm text-muted-foreground">
                    {r.duration_weeks ?? "—"}
                  </TableCell>
                  <TableCell>
                    {findUrl && (
                      <Link href={findUrl} title="Find candidates for this role">
                        <Sparkles
                          className="w-3.5 h-3.5 transition-colors"
                          style={{ color: "#CBD5E1" }}
                          onMouseEnter={e => (e.currentTarget.style.color = "#3411A3")}
                          onMouseLeave={e => (e.currentTarget.style.color = "#CBD5E1")}
                        />
                      </Link>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

// ── Page shell ─────────────────────────────────────────────────────────────
export default function ForecastPage() {
  const [tab, setTab] = useState<"pipeline" | "outlook">("pipeline");
  const { data: pipelineData } = useForecast();
  const { data: outlookData = [], isLoading: outlookLoading } = useForecastOutlook();

  const total = pipelineData?.length ?? 0;
  const highProb = pipelineData?.filter((r) => (r.probability_weight ?? 0) >= 0.7).length ?? 0;
  const avgProb = pipelineData && pipelineData.length
    ? pipelineData.reduce((s, r) => s + (r.probability_weight ?? 0), 0) / pipelineData.length
    : 0;

  const TABS = [
    { key: "pipeline", label: "Pipeline Requests", icon: BarChart3 },
    { key: "outlook",  label: "6-Month Outlook",   icon: TrendingUp },
  ] as const;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Forecast / Pipeline"
        subtitle={`${total} resource requests · ${highProb} high probability`}
      />

      <div className="px-8 pt-6 pb-8">
        {/* KPI strip */}
        <div className="grid grid-cols-3 gap-4 mb-7">
          <ForecastKpi
            label="Open Requests"
            value={total}
            sub="Total pipeline roles"
            accent="#3411A3"
            icon={BarChart3}
          />
          <ForecastKpi
            label="High Probability"
            value={highProb}
            sub="Win probability ≥ 70%"
            accent="#3411A3"
            icon={Target}
          />
          <ForecastKpi
            label="Avg Probability"
            value={`${Math.round(avgProb * 100)}%`}
            sub="Across all requests"
            accent="#A16BDB"
            icon={TrendingUp}
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all"
              style={
                tab === t.key
                  ? { background: "#19105B", color: "#fff", boxShadow: "0 1px 4px rgba(25,16,91,0.2)" }
                  : { background: "#F1F5F9", color: "#64748B" }
              }
            >
              <t.icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          ))}
        </div>

        {tab === "pipeline" && <PipelineList />}
        {tab === "outlook" && (
          outlookLoading
            ? (
              <div className="py-12 text-sm text-muted-foreground flex items-center gap-2">
                <TrendingUp className="w-4 h-4 animate-pulse" /> Loading outlook…
              </div>
            )
            : <OutlookChart months={outlookData} />
        )}
      </div>
    </div>
  );
}
