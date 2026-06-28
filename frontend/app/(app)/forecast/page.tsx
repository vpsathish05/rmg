"use client";
import { useState, useMemo } from "react";
import { useForecast, useForecastOutlook, useForecastInsights, type OutlookMonth } from "@/lib/hooks";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Sparkles, TrendingUp, Target, BarChart3, Search, AlertTriangle, Clock, DollarSign, Users, Calendar } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  AreaChart, Area, LineChart, Line, CartesianGrid, Legend,
} from "recharts";

export default function ForecastPage() {
  const [tab, setTab] = useState<"insights" | "pipeline" | "outlook">("insights");
  const { data: pipelineData } = useForecast();
  const { data: outlookData = [], isLoading: outlookLoading } = useForecastOutlook();
  const { data: insights } = useForecastInsights();

  const total = pipelineData?.length ?? 0;
  const highProb = pipelineData?.filter(r => (r.probability_weight ?? 0) >= 0.7).length ?? 0;

  return (
    <div className="flex flex-col h-full">
      <div className="px-8 py-5 bg-white border-b border-gray-100 shrink-0">
        <h1 className="text-xl font-bold" style={{ color: "#19105B" }}>Forecast</h1>
        <p className="text-xs text-gray-400 mt-0.5">{total} resource requests · {highProb} high probability</p>
      </div>

      <div className="px-6 pt-4 pb-8 overflow-y-auto flex-1 space-y-5">
        {/* Alerts */}
        {insights?.alerts && insights.alerts.length > 0 && (
          <div className="space-y-2">
            {insights.alerts.map((a, i) => (
              <div key={i} className="rounded-xl p-3 flex items-center gap-3 border" style={{
                background: a.type === "urgent" ? "#FF61960a" : a.type === "revenue" ? "#19105B08" : "#19105B05",
                borderColor: a.type === "urgent" ? "#FF619630" : "#19105B15",
              }}>
                <AlertTriangle className="w-4 h-4 shrink-0" style={{ color: a.type === "urgent" ? "#FF6196" : "#19105B" }} />
                <span className="text-xs font-medium" style={{ color: "#19105B" }}>{a.message}</span>
              </div>
            ))}
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-2xl p-4 border border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Revenue at Risk</p>
              <DollarSign className="w-4 h-4" style={{ color: "#FF6196" }} />
            </div>
            <p className="text-2xl font-bold tabular-nums" style={{ color: "#FF6196" }}>
              ${((insights?.revenue_at_risk ?? 0) / 1000).toFixed(0)}K
            </p>
            <p className="text-[10px] text-gray-400 mt-0.5">Unresourced weighted pipeline</p>
          </div>
          <div className="bg-white rounded-2xl p-4 border border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Unresourced</p>
              <Users className="w-4 h-4" style={{ color: "#19105B" }} />
            </div>
            <p className="text-2xl font-bold tabular-nums" style={{ color: "#19105B" }}>{insights?.unresourced_roles ?? 0}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">{insights?.weighted_fte?.toFixed(1) ?? 0} weighted FTE</p>
          </div>
          <div className="bg-white rounded-2xl p-4 border border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">High Probability</p>
              <Target className="w-4 h-4" style={{ color: "#19105B" }} />
            </div>
            <p className="text-2xl font-bold tabular-nums" style={{ color: "#19105B" }}>{highProb}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">Win probability ≥ 70%</p>
          </div>
          <div className="bg-white rounded-2xl p-4 border border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Hot Deals</p>
              <Calendar className="w-4 h-4" style={{ color: "#FF6196" }} />
            </div>
            <p className="text-2xl font-bold tabular-nums" style={{ color: "#FF6196" }}>{insights?.hot_deals?.length ?? 0}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">Starting within 3 months</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl w-fit">
          {([
            { key: "insights", label: "Insights", icon: Sparkles },
            { key: "pipeline", label: "Pipeline", icon: BarChart3 },
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

        {tab === "insights" && insights && <InsightsView insights={insights} />}
        {tab === "pipeline" && <PipelineList />}
        {tab === "outlook" && (outlookLoading
          ? <div className="py-12 text-sm text-gray-400 flex items-center gap-2"><TrendingUp className="w-4 h-4 animate-pulse" /> Loading…</div>
          : <OutlookChart months={outlookData} />
        )}
      </div>
    </div>
  );
}


// ── Insights View ──────────────────────────────────────────────────────────
function InsightsView({ insights }: { insights: NonNullable<ReturnType<typeof useForecastInsights>["data"]> }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Capacity Gap */}
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Capacity Gap (Next 3 Months)</h3>
          <p className="text-[10px] text-gray-400 mb-3">Demand FTE vs bench availability by role</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={insights.capacity_gap} layout="vertical" margin={{ left: 0, right: 16 }}>
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="role" tick={{ fontSize: 10 }} width={110} />
                <Tooltip />
                <Bar dataKey="demand" fill="#19105B" name="Demand FTE" barSize={10} radius={[0, 4, 4, 0]} />
                <Bar dataKey="bench" fill="#FF6196" name="Bench" barSize={10} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Funnel by Stage */}
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Pipeline Funnel (Not Resourced)</h3>
          <p className="text-[10px] text-gray-400 mb-3">Roles by deal stage — weighted FTE</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={insights.funnel} layout="vertical" margin={{ left: 0, right: 16 }}>
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="stage" tick={{ fontSize: 10 }} width={100} />
                <Tooltip />
                <Bar dataKey="weighted_fte" name="Weighted FTE" barSize={16} radius={[0, 6, 6, 0]}>
                  {insights.funnel.map((_, i) => (
                    <Cell key={i} fill={i === 0 ? "#19105B" : i === 1 ? "#19105BCC" : i === 2 ? "#19105B99" : "#19105B66"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Hot Deals Timeline */}
      <div className="bg-white rounded-2xl p-5 border border-gray-100">
        <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Hot Deals — Starting Soon (≥70% probability)</h3>
        <p className="text-[10px] text-gray-400 mb-4">Unresourced roles with high win probability, ordered by start date</p>
        {insights.hot_deals.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">No high-probability deals starting within 3 months</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {insights.hot_deals.map((d, i) => (
              <div key={i} className="rounded-xl border p-3 flex flex-col gap-1" style={{ borderColor: "#FF619630", background: "#FF61960a" }}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold" style={{ color: "#19105B" }}>{d.client}</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: "#19105B", color: "#fff" }}>
                    {d.probability ? `${Math.round(d.probability * 100)}%` : "—"}
                  </span>
                </div>
                <span className="text-[11px] text-gray-600">{d.role}</span>
                <div className="flex items-center gap-3 text-[10px] text-gray-400 mt-1">
                  {d.start_date && <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(d.start_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</span>}
                  {d.duration_weeks && <span>{d.duration_weeks}w</span>}
                  <span>{d.allocation_pct}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


// ── Outlook Chart (existing, unchanged) ────────────────────────────────────
const TOP_ROLES_N = 5;
const ROLE_COLORS = ["#19105B", "#FF6196", "#19105B99", "#FF619699", "#19105B66", "#FF619666"];

function OutlookChart({ months }: { months: OutlookMonth[] }) {
  const allRoles = useMemo(() => {
    const totals: Record<string, number> = {};
    months.forEach(m => m.roles.forEach(r => { totals[r.role] = (totals[r.role] ?? 0) + r.total_fte; }));
    return Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, TOP_ROLES_N).map(([r]) => r);
  }, [months]);
  const maxFte = useMemo(() => Math.max(...months.map(m => m.total_fte), 1), [months]);

  const revenueData = useMemo(() => {
    const RATE = 12000;
    return months.map(m => ({
      month: m.month.slice(5),
      raw_fte: m.total_fte,
      weighted_fte: m.weighted_fte,
      revenue: Math.round(m.weighted_fte * RATE / 1000),
    }));
  }, [months]);

  if (!months.length) return <div className="py-20 text-center text-sm text-gray-400">No pipeline starts in the next 6 months.</div>;

  const BAR_H = 180, BAR_W = 56, GAP = 28, LABEL_H = 36;
  const svgW = months.length * (BAR_W + GAP) + GAP;
  const svgH = BAR_H + LABEL_H + 24;

  return (
    <div className="space-y-6">
      {/* Revenue Projection + FTE Gap */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Revenue Projection (Weighted)</h3>
          <p className="text-[10px] text-gray-400 mb-3">Monthly potential revenue at $12K/FTE — probability-weighted</p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f5" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => `$${v}K`} />
                <Tooltip formatter={(v: number) => `$${v}K`} />
                <Area type="monotone" dataKey="revenue" stroke="#19105B" fill="#19105B20" strokeWidth={2} name="Revenue ($K)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Raw vs Weighted FTE</h3>
          <p className="text-[10px] text-gray-400 mb-3">Total requested FTE vs probability-adjusted reality</p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f5" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="raw_fte" stroke="#19105B" strokeWidth={2} dot={{ r: 3 }} name="Raw FTE (requested)" />
                <Line type="monotone" dataKey="weighted_fte" stroke="#FF6196" strokeWidth={2} dot={{ r: 3 }} name="Weighted FTE (likely)" strokeDasharray="5 5" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Existing stacked bar */}
      <div className="bg-white rounded-2xl p-5 border border-gray-100">
        <h3 className="text-xs font-bold mb-3" style={{ color: "#19105B" }}>FTE Demand by Role</h3>
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
      </div>
    </div>
  );
}


// ── Pipeline List (existing) ───────────────────────────────────────────────
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
          className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-gray-50 border border-gray-200 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300 transition-all" style={{ color: "#19105B" }} />
      </div>
      <div className="rounded-2xl border border-gray-100 overflow-hidden overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              {["Client", "Role", "Alloc", "SOW", "Prob", "Start", "Weeks"].map(h => (
                <TableHead key={h} className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">{h}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow><TableCell colSpan={7} className="text-center py-12 text-gray-400 text-xs">No results</TableCell></TableRow>
            ) : filtered.map(r => (
              <TableRow key={r.id} className="hover:bg-gray-50/50 transition-colors">
                <TableCell>
                  <p className="text-xs font-semibold" style={{ color: "#19105B" }}>{r.client_name ?? "—"}</p>
                  <p className="text-[10px] text-gray-400">{r.solution ?? ""}</p>
                </TableCell>
                <TableCell className="text-xs font-mono text-gray-700">{r.role_code_raw ?? "—"}</TableCell>
                <TableCell className="text-center tabular-nums text-xs text-gray-500">{r.allocation_pct != null ? `${r.allocation_pct}%` : "—"}</TableCell>
                <TableCell className="text-center">
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${r.sow_signed ? "text-white" : "bg-gray-50 text-gray-400 border border-gray-100"}`}
                    style={r.sow_signed ? { background: "#19105B" } : undefined}>
                    {r.sow_signed ? "Yes" : "No"}
                  </span>
                </TableCell>
                <TableCell className="text-right tabular-nums text-xs font-bold" style={{ color: (r.probability_weight ?? 0) >= 0.7 ? "#19105B" : "#94A3B8" }}>
                  {r.probability_weight != null ? `${Math.round(r.probability_weight * 100)}%` : "—"}
                </TableCell>
                <TableCell className="text-xs text-gray-500">{r.likely_start_date ?? "—"}</TableCell>
                <TableCell className="text-center tabular-nums text-xs text-gray-500">{r.duration_weeks ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
