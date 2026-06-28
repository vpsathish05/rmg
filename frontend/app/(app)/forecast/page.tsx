"use client";
import { useState, useMemo } from "react";
import Link from "next/link";
import { useForecast, useForecastOutlook, type OutlookMonth } from "@/lib/hooks";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Sparkles, TrendingUp, Target, BarChart3, Search } from "lucide-react";

function probColor(p: number | null): string {
  if (!p) return "#94A3B8";
  if (p >= 0.9) return "#059669";
  if (p >= 0.7) return "#19105B";
  if (p >= 0.5) return "#d97706";
  return "#94A3B8";
}

function ForecastKpi({ label, value, sub, accent, icon: Icon }: {
  label: string; value: string | number; sub?: string; accent: string; icon: React.ElementType;
}) {
  return (
    <div className="bg-white rounded-2xl p-5 border border-gray-100 hover:shadow-md transition-all">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">{label}</p>
        <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: `${accent}12` }}>
          <Icon className="w-4 h-4" style={{ color: accent }} />
        </div>
      </div>
      <p className="text-4xl font-bold tabular-nums text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}


const TOP_ROLES_N = 5;
const ROLE_COLORS = ["#19105B", "#FF6196", "#19105B99", "#FF619699", "#19105B66", "#FF619666"];

function OutlookChart({ months }: { months: OutlookMonth[] }) {
  const allRoles = useMemo(() => {
    const totals: Record<string, number> = {};
    months.forEach(m => m.roles.forEach(r => { totals[r.role] = (totals[r.role] ?? 0) + r.total_fte; }));
    return Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, TOP_ROLES_N).map(([r]) => r);
  }, [months]);
  const maxFte = useMemo(() => Math.max(...months.map(m => m.total_fte), 1), [months]);

  if (!months.length) return <div className="py-20 text-center text-sm text-gray-400">No pipeline starts in the next 6 months.</div>;

  const BAR_H = 180, BAR_W = 56, GAP = 28, LABEL_H = 36;
  const svgW = months.length * (BAR_W + GAP) + GAP;
  const svgH = BAR_H + LABEL_H + 24;

  return (
    <div>
      <div className="flex flex-wrap gap-4 mb-5">
        {allRoles.map((role, i) => (
          <div key={role} className="flex items-center gap-2 text-xs text-gray-500">
            <span className="w-3 h-3 rounded-sm" style={{ background: ROLE_COLORS[i] }} /> {role}
          </div>
        ))}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span className="w-3 h-3 rounded-sm bg-gray-200" /> Other
        </div>
      </div>
      <div className="rounded-2xl p-6 overflow-x-auto bg-gray-50 border border-gray-100">
        <svg width={svgW} height={svgH} style={{ overflow: "visible" }}>
          {[0.25, 0.5, 0.75, 1].map(f => (
            <line key={f} x1={0} y1={BAR_H * (1 - f)} x2={svgW} y2={BAR_H * (1 - f)} stroke="#e5e7eb" strokeWidth={1} strokeDasharray="3 3" />
          ))}
          {months.map((m, mi) => {
            const x = GAP + mi * (BAR_W + GAP);
            let yOffset = BAR_H;
            const slices: { role: string; h: number; color: string; isFirst: boolean }[] = [];
            const roleMap: Record<string, number> = {};
            m.roles.forEach(r => { roleMap[r.role] = r.total_fte; });
            let otherFte = m.total_fte;
            allRoles.forEach((role, ri) => {
              const fte = roleMap[role] ?? 0;
              if (fte > 0) { slices.push({ role, h: Math.round((fte / maxFte) * BAR_H), color: ROLE_COLORS[ri], isFirst: false }); otherFte -= fte; }
            });
            if (otherFte > 0.05) slices.push({ role: "Other", h: Math.round((otherFte / maxFte) * BAR_H), color: "#d1d5db", isFirst: false });
            slices.reverse();
            if (slices.length) slices[0] = { ...slices[0], isFirst: true };
            return (
              <g key={m.month}>
                {slices.map(s => { yOffset -= s.h; return <rect key={s.role} x={x} y={yOffset} width={BAR_W} height={s.h} fill={s.color} rx={s.isFirst ? 6 : 0} />; })}
                <text x={x + BAR_W / 2} y={yOffset - 7} textAnchor="middle" fontSize={11} fontWeight="600" fill="#374151">{m.weighted_fte.toFixed(1)}</text>
                <text x={x + BAR_W / 2} y={BAR_H + LABEL_H - 14} textAnchor="middle" fontSize={12} fontWeight="500" fill="#6b7280">{m.month.slice(5)}</text>
              </g>
            );
          })}
          <line x1={0} y1={BAR_H} x2={svgW} y2={BAR_H} stroke="#d1d5db" strokeWidth={1.5} />
        </svg>
      </div>


      {/* Summary table */}
      <div className="mt-6 rounded-2xl border border-gray-100 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Month</TableHead>
              <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Top Role</TableHead>
              <TableHead className="text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">Requests</TableHead>
              <TableHead className="text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">Total FTE</TableHead>
              <TableHead className="text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">Weighted</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {months.map((m, i) => (
              <TableRow key={m.month} className="hover:bg-gray-50/50 transition-colors">
                <TableCell className="font-mono text-sm font-medium text-gray-700">{m.month}</TableCell>
                <TableCell className="text-sm text-gray-500">{m.roles[0]?.role ?? "—"}</TableCell>
                <TableCell className="text-right tabular-nums text-sm text-gray-600">{m.roles.reduce((s, r) => s + r.request_count, 0)}</TableCell>
                <TableCell className="text-right tabular-nums text-sm font-bold" style={{ color: "#19105B" }}>{m.total_fte.toFixed(1)}</TableCell>
                <TableCell className="text-right tabular-nums text-sm text-gray-500">{m.weighted_fte.toFixed(1)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}


function PipelineList() {
  const [search, setSearch] = useState("");
  const { data, isLoading } = useForecast();

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!search) return data;
    const q = search.toLowerCase();
    return data.filter(r =>
      (r.client_name ?? "").toLowerCase().includes(q) ||
      (r.role_code_raw ?? "").toLowerCase().includes(q) ||
      (r.solution ?? "").toLowerCase().includes(q)
    );
  }, [data, search]);

  if (isLoading) return <div className="py-12 text-sm text-gray-400 flex items-center gap-2"><BarChart3 className="w-4 h-4 animate-pulse" /> Loading…</div>;

  return (
    <>
      <div className="mb-5 relative max-w-sm">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search client, role, solution…"
          className="w-full pl-9 pr-3 py-2 text-sm rounded-xl bg-gray-50 border border-gray-200 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300 transition-all" />
      </div>
      <div className="rounded-2xl border border-gray-100 overflow-hidden overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Client</TableHead>
              <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Role</TableHead>
              <TableHead className="text-center text-[10px] font-semibold uppercase tracking-wider text-gray-400">Alloc</TableHead>
              <TableHead className="text-center text-[10px] font-semibold uppercase tracking-wider text-gray-400">SOW</TableHead>
              <TableHead className="text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">Prob</TableHead>
              <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Start</TableHead>
              <TableHead className="text-center text-[10px] font-semibold uppercase tracking-wider text-gray-400">Weeks</TableHead>
              <TableHead className="w-8" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow><TableCell colSpan={8} className="text-center py-12 text-gray-400 text-sm">No results</TableCell></TableRow>
            ) : filtered.map(r => {
              const findUrl = r.role_code_raw ? `/recommend?role_code=${encodeURIComponent(r.role_code_raw)}` : null;
              return (
                <TableRow key={r.id} className="hover:bg-violet-50/30 transition-colors">
                  <TableCell>
                    <p className="text-sm font-semibold text-gray-900">{r.client_name ?? "—"}</p>
                    <p className="text-[10px] text-gray-400">{r.solution ?? ""}</p>
                  </TableCell>
                  <TableCell className="text-sm font-mono text-gray-700">{r.role_code_raw ?? "—"}</TableCell>
                  <TableCell className="text-center tabular-nums text-sm text-gray-500">{r.allocation_pct != null ? `${r.allocation_pct}%` : "—"}</TableCell>
                  <TableCell className="text-center">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${r.sow_signed ? "bg-emerald-50 text-emerald-600 border border-emerald-100" : "bg-gray-50 text-gray-400 border border-gray-100"}`}>
                      {r.sow_signed ? "Yes" : "No"}
                    </span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm font-bold" style={{ color: probColor(r.probability_weight) }}>
                    {r.probability_weight != null ? `${Math.round(r.probability_weight * 100)}%` : "—"}
                  </TableCell>
                  <TableCell className="text-xs text-gray-500">{r.likely_start_date ?? "—"}</TableCell>
                  <TableCell className="text-center tabular-nums text-sm text-gray-500">{r.duration_weeks ?? "—"}</TableCell>
                  <TableCell>
                    {findUrl && <Link href={findUrl}><Sparkles className="w-3.5 h-3.5 text-gray-300 hover:text-violet-500 transition-colors" /></Link>}
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


export default function ForecastPage() {
  const [tab, setTab] = useState<"pipeline" | "outlook">("pipeline");
  const { data: pipelineData } = useForecast();
  const { data: outlookData = [], isLoading: outlookLoading } = useForecastOutlook();

  const total = pipelineData?.length ?? 0;
  const highProb = pipelineData?.filter(r => (r.probability_weight ?? 0) >= 0.7).length ?? 0;
  const avgProb = pipelineData?.length ? pipelineData.reduce((s, r) => s + (r.probability_weight ?? 0), 0) / pipelineData.length : 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 py-6 bg-white border-b border-gray-100">
        <h1 className="text-xl font-bold text-gray-900">Forecast</h1>
        <p className="text-sm text-gray-400 mt-0.5">{total} resource requests · {highProb} high probability</p>
      </div>

      <div className="px-8 pt-6 pb-8 overflow-y-auto flex-1">
        {/* KPIs */}
        <div className="grid grid-cols-3 gap-4 mb-7">
          <ForecastKpi label="Open Requests" value={total} sub="Total pipeline roles" accent="#19105B" icon={BarChart3} />
          <ForecastKpi label="High Probability" value={highProb} sub="Win probability ≥ 70%" accent="#19105B" icon={Target} />
          <ForecastKpi label="Avg Probability" value={`${Math.round(avgProb * 100)}%`} sub="Across all requests" accent="#FF6196" icon={TrendingUp} />
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl w-fit mb-6">
          {([
            { key: "pipeline", label: "Pipeline Requests", icon: BarChart3 },
            { key: "outlook", label: "6-Month Outlook", icon: TrendingUp },
          ] as const).map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
                tab === t.key ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}>
              <t.icon className="w-3.5 h-3.5" /> {t.label}
            </button>
          ))}
        </div>

        {tab === "pipeline" && <PipelineList />}
        {tab === "outlook" && (outlookLoading
          ? <div className="py-12 text-sm text-gray-400 flex items-center gap-2"><TrendingUp className="w-4 h-4 animate-pulse" /> Loading…</div>
          : <OutlookChart months={outlookData} />
        )}
      </div>
    </div>
  );
}
