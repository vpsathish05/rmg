"use client";
import { useState, useMemo } from "react";
import { useForecast, useForecastOutlook, useForecastInsights, useMLRevenueForecast, useMLClusterForecast, useMLResourceForecast, useMLCOEGap, useMLProjectForecast, useMLActuals, type OutlookMonth } from "@/lib/hooks";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Sparkles, TrendingUp, Target, BarChart3, Search, AlertTriangle, Clock, DollarSign, Users, Calendar, Brain, FileText, X } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  AreaChart, Area, LineChart, Line, CartesianGrid, Legend,
} from "recharts";

export default function ForecastPage() {
  const [tab, setTab] = useState<"ai" | "insights" | "pipeline" | "outlook">("ai");
  const [showDocModal, setShowDocModal] = useState(false);
  const { data: pipelineData } = useForecast();
  const { data: outlookData = [], isLoading: outlookLoading } = useForecastOutlook();
  const { data: insights } = useForecastInsights();

  const total = pipelineData?.length ?? 0;
  const highProb = pipelineData?.filter(r => (r.probability_weight ?? 0) >= 0.7).length ?? 0;

  return (
    <div className="flex flex-col h-full">
      <div className="px-8 py-5 bg-white border-b border-gray-100 shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ color: "#19105B" }}>Forecast</h1>
          <p className="text-xs text-gray-400 mt-0.5">{total} resource requests · {highProb} high probability</p>
        </div>
        <button
          onClick={() => setShowDocModal(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl border border-gray-200 text-gray-600 hover:border-gray-300 hover:text-gray-900 transition-all"
        >
          <FileText className="w-3 h-3" /> How It Works
        </button>
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
            { key: "ai", label: "AI Forecast", icon: Brain },
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

        {tab === "ai" && <AIForecastView />}
        {tab === "insights" && insights && <InsightsView insights={insights} />}
        {tab === "pipeline" && <PipelineList />}
        {tab === "outlook" && (outlookLoading
          ? <div className="py-12 text-sm text-gray-400 flex items-center gap-2"><TrendingUp className="w-4 h-4 animate-pulse" /> Loading…</div>
          : <OutlookChart months={outlookData} />
        )}
      </div>

      {/* How It Works Modal */}
      {showDocModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowDocModal(false)}>
          <div className="relative w-[92vw] h-[90vh] bg-white shadow-2xl flex flex-col overflow-hidden rounded-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-3 shrink-0" style={{ background: "#19105B" }}>
              <div className="flex items-center gap-3">
                <Brain className="w-4 h-4 text-white" />
                <span className="text-sm font-bold text-white">Cluster Revenue & COE Forecast Engine — How It Works</span>
              </div>
              <button onClick={() => setShowDocModal(false)} className="w-8 h-8 flex items-center justify-center text-white opacity-70 hover:opacity-100 transition-all">
                <X className="w-5 h-5" />
              </button>
            </div>
            <iframe src="/forecast-flow.html" className="flex-1 w-full border-none" title="Forecast Flow Documentation" />
          </div>
        </div>
      )}
    </div>
  );
}


// ── AI Forecast View ───────────────────────────────────────────────────────
function AIForecastView() {
  const { data: revenue, isLoading: revLoading } = useMLRevenueForecast();
  const { data: clusters } = useMLClusterForecast();
  const { data: resources } = useMLResourceForecast();
  const { data: coeGap } = useMLCOEGap();
  const { data: projects } = useMLProjectForecast();
  const { data: actuals } = useMLActuals();

  // Revenue chart data: actuals + forecast
  const revenueChartData = useMemo(() => {
    if (!revenue || !actuals) return [];
    const data: { month: string; actual?: number; p10?: number; p50?: number; p90?: number }[] = [];
    // Last 6 actuals
    for (const a of actuals.actuals.slice(-6)) {
      data.push({ month: a.month.slice(5), actual: a.revenue / 1e6 });
    }
    // Forecast
    for (const f of revenue.forecasts) {
      data.push({ month: f.month.slice(5), p10: f.p10 / 1e6, p50: f.p50 / 1e6, p90: f.p90 / 1e6 });
    }
    return data;
  }, [revenue, actuals]);

  // Cluster stacked area
  const clusterData = useMemo(() => {
    if (!clusters) return [];
    const months = clusters.clusters["1"]?.map(c => c.month) ?? [];
    return months.map((month, i) => {
      const row: Record<string, unknown> = { month: month.slice(5) };
      for (const [cl, ms] of Object.entries(clusters.clusters)) {
        row[`Cluster ${cl}`] = (ms[i]?.revenue_p50 ?? 0) / 1e6;
      }
      return row;
    });
  }, [clusters]);

  // COE gap data
  const coeGapData = useMemo(() => {
    if (!coeGap) return [];
    return Object.entries(coeGap.total_gap_by_coe)
      .map(([coe, gap]) => ({
        coe,
        gap: Number(gap),
        demand: coeGap.total_demand_by_coe[coe] ?? 0,
        supply: coeGap.total_supply_by_coe[coe] ?? 0,
      }))
      .filter(d => d.demand > 0 || d.supply > 0)
      .sort((a, b) => a.gap - b.gap);
  }, [coeGap]);

  // Resource utilization
  const utilData = useMemo(() => {
    if (!resources) return [];
    return resources.months.map(m => ({
      month: m.month.slice(5),
      fte: m.total_fte,
      bench: m.bench_count,
      util: m.utilization_pct,
    }));
  }, [resources]);

  if (revLoading) return <div className="py-12 text-sm text-gray-400 flex items-center gap-2"><Brain className="w-4 h-4 animate-pulse" /> Loading AI forecast models…</div>;

  return (
    <div className="space-y-5">
      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">12-Mo Revenue (P50)</p>
          <p className="text-xl font-bold mt-1" style={{ color: "#19105B" }}>${((revenue?.annual_total_p50 ?? 0) / 1e6).toFixed(1)}M</p>
          <p className="text-[10px] text-gray-400">YoY: +{((revenue?.growth_rate_yoy ?? 0) * 100).toFixed(0)}%</p>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Projects (12mo)</p>
          <p className="text-xl font-bold mt-1" style={{ color: "#19105B" }}>{projects?.annual_total_p50 ?? 0}</p>
          <p className="text-[10px] text-gray-400">Avg {projects?.avg_monthly?.toFixed(0)}/mo</p>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Avg FTE Demand</p>
          <p className="text-xl font-bold mt-1" style={{ color: "#19105B" }}>{resources?.avg_monthly_fte?.toFixed(0) ?? 0}</p>
          <p className="text-[10px] text-gray-400">Util: {resources?.avg_utilization?.toFixed(0)}%</p>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Hiring Need</p>
          <p className="text-xl font-bold mt-1" style={{ color: "#FF6196" }}>{coeGap ? Object.values(coeGap.hiring_needs).reduce((s, v) => s + v, 0) : 0}</p>
          <p className="text-[10px] text-gray-400">Across COEs</p>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Model MAPE</p>
          <p className="text-xl font-bold mt-1" style={{ color: "#19105B" }}>{revenue?.train_mape?.toFixed(1)}%</p>
          <p className="text-[10px] text-gray-400">{revenue?.training_months} months trained</p>
        </div>
      </div>

      {/* Revenue Forecast Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Revenue Forecast (P10/P50/P90)</h3>
          <p className="text-[10px] text-gray-400 mb-3">Actuals → 12-month ML prediction with confidence bands</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={revenueChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f5" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => `$${v.toFixed(1)}M`} />
                <Tooltip formatter={(v: number) => `$${v.toFixed(2)}M`} />
                <Area type="monotone" dataKey="p90" stroke="none" fill="#19105B15" name="P90" />
                <Area type="monotone" dataKey="p50" stroke="#19105B" fill="#19105B30" strokeWidth={2} name="Forecast (P50)" />
                <Area type="monotone" dataKey="p10" stroke="none" fill="#FFFFFF" name="P10" />
                <Line type="monotone" dataKey="actual" stroke="#FF6196" strokeWidth={2.5} dot={{ r: 4 }} name="Actual" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Cluster Revenue */}
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Revenue by Cluster</h3>
          <p className="text-[10px] text-gray-400 mb-3">12-month forecast decomposed by business cluster</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={clusterData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f5" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => `$${v.toFixed(1)}M`} />
                <Tooltip formatter={(v: number) => `$${v.toFixed(2)}M`} />
                <Area type="monotone" dataKey="Cluster 5" stackId="1" fill="#19105B" stroke="#19105B" name="Cluster 5" />
                <Area type="monotone" dataKey="Cluster 3" stackId="1" fill="#3411A3" stroke="#3411A3" name="Cluster 3" />
                <Area type="monotone" dataKey="Cluster 1" stackId="1" fill="#FF6196" stroke="#FF6196" name="Cluster 1" />
                <Area type="monotone" dataKey="Cluster 2" stackId="1" fill="#71EAE1" stroke="#71EAE1" name="Cluster 2" />
                <Area type="monotone" dataKey="Cluster 4" stackId="1" fill="#A16BDB" stroke="#A16BDB" name="Cluster 4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Resource & COE Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Utilization */}
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>FTE Demand & Utilization</h3>
          <p className="text-[10px] text-gray-400 mb-3">Projected allocation vs bench (12 months)</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={utilData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f5" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="fte" fill="#19105B" name="Billable FTE" radius={[4, 4, 0, 0]} />
                <Bar dataKey="bench" fill="#FF619640" name="Bench" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* COE Gap */}
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>COE Supply vs Demand Gap</h3>
          <p className="text-[10px] text-gray-400 mb-3">Negative = shortfall (FTE-months over 12 months)</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={coeGapData} layout="vertical" margin={{ left: 10, right: 16 }}>
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="coe" tick={{ fontSize: 9 }} width={130} />
                <Tooltip />
                <Bar dataKey="gap" name="Gap (FTE-months)" barSize={14} radius={[0, 4, 4, 0]}>
                  {coeGapData.map((d, i) => (
                    <Cell key={i} fill={d.gap < 0 ? "#FF6196" : "#19105B"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Hiring & Project Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Hiring Recommendations */}
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Hiring Recommendations</h3>
          <p className="text-[10px] text-gray-400 mb-3">Roles where peak demand exceeds 80% of current capacity</p>
          <div className="space-y-2 max-h-52 overflow-y-auto">
            {resources && Object.entries(resources.hiring_gap)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 8)
              .map(([role, count]) => (
                <div key={role} className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50">
                  <span className="text-xs font-medium" style={{ color: "#19105B" }}>{role}</span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full text-white" style={{ background: "#FF6196" }}>+{count}</span>
                </div>
              ))}
          </div>
        </div>

        {/* Project Forecast */}
        <div className="bg-white rounded-2xl p-5 border border-gray-100">
          <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Project Volume Forecast</h3>
          <p className="text-[10px] text-gray-400 mb-3">Monthly new project starts — historical + 12-month prediction</p>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                ...(projects?.historical?.map(h => ({ month: h.month.slice(5), actual: h.count })) ?? []),
                ...(projects?.forecasts?.map(f => ({ month: f.month.slice(5), forecast: f.p50 })) ?? []),
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f5" />
                <XAxis dataKey="month" tick={{ fontSize: 9 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="actual" fill="#19105B" name="Actual" radius={[3, 3, 0, 0]} />
                <Bar dataKey="forecast" fill="#19105B40" name="Forecast" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Model info footer */}
      <div className="text-[10px] text-gray-400 pt-2">
        Models: {revenue?.method} · {projects?.method} · {resources?.method} | Last actual: {revenue?.last_actual_month}
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.hot_deals.map((d: any, i: number) => (
              <div key={i} className="rounded-xl border overflow-hidden" style={{ borderColor: "#19105B20" }}>
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3" style={{ background: "#19105B08" }}>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold" style={{ color: "#19105B" }}>{d.client}</span>
                    {d.start_date && (
                      <span className="text-[10px] text-gray-400 flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(d.start_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</span>
                    )}
                  </div>
                  <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full text-white" style={{ background: "#19105B" }}>
                    {d.probability ? `${Math.round(d.probability * 100)}%` : "—"}
                  </span>
                </div>
                {/* Roles */}
                <div className="px-4 py-2.5 space-y-1.5">
                  {(d.roles || []).map((r: any, ri: number) => (
                    <div key={ri} className="flex items-center justify-between">
                      <span className="text-[11px] font-medium" style={{ color: "#19105B" }}>{r.role ?? "—"}</span>
                      <div className="flex items-center gap-2 text-[10px] text-gray-400">
                        <span>{r.allocation_pct}%</span>
                        {r.duration_weeks && <span>{r.duration_weeks}w</span>}
                      </div>
                    </div>
                  ))}
                  {!d.roles && d.role && <span className="text-[11px]" style={{ color: "#19105B" }}>{d.role}</span>}
                </div>
                {/* Footer */}
                <div className="px-4 py-2 border-t text-[10px] text-gray-400" style={{ borderColor: "#19105B10" }}>
                  {(d.roles || []).length} role{(d.roles || []).length !== 1 ? "s" : ""} needed
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
