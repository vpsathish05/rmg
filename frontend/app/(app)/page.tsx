"use client";
import { useState, useEffect } from "react";
import { useDashboardSummary, useDashboardCharts, useDataHealth } from "@/lib/hooks";
import { Users, FolderKanban, TrendingUp, Sparkles, AlertTriangle, CheckCircle2, Clock, Info, X, Loader2, Activity, PoundSterling } from "lucide-react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip,
  LineChart, Line, CartesianGrid, Legend,
} from "recharts";
import api from "@/lib/api";

const COLORS = {
  primary: "#19105B",    // Midnight Blue
  secondary: "#FF6196",  // Rose
  bench: "#19105B",
  partial: "#FF6196",
  allocated: "#19105B",
  red: "#dc2626",
  amber: "#d97706",
  green: "#059669",
};

interface DrillDownData { title: string; explanation: string; columns: string[]; data: Record<string, unknown>[] }
interface DrillTarget { chart: string; status?: string }

function DrillDownModal({ target, onClose }: { target: DrillTarget; onClose: () => void }) {
  const [data, setData] = useState<DrillDownData | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [colFilters, setColFilters] = useState<Record<string, string>>({});

  useEffect(() => {
    setData(null); setLoading(true); setSearch(""); setSortCol(null); setColFilters({});
    const kpis = ["active_employees", "on_bench", "partially_available", "open_pipeline", "high_probability", "active_projects", "billable", "unbillable", "over_allocated"];
    const dataHealthGaps = ["skills", "pipeline_duration", "pipeline_skills", "competency", "project_coe", "coe_tags", "timesheets", "embeddings", "employee_metadata"];
    let url: string;
    if (dataHealthGaps.includes(target.chart)) {
      url = `/api/dashboard/data-health/detail?gap=${target.chart}`;
    } else if (kpis.includes(target.chart)) {
      url = `/api/dashboard/kpi/detail?kpi=${target.chart}`;
    } else {
      const base = `/api/dashboard/charts/detail?chart=${target.chart}`;
      url = target.status ? `${base}&status=${encodeURIComponent(target.status)}` : base;
    }
    api.get(url).then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, [target.chart, target.status]);

  const rows = data?.data ?? [];
  const filtered = rows.filter(row => {
    for (const [col, val] of Object.entries(colFilters)) {
      if (val && String(row[col] ?? "") !== val) return false;
    }
    if (!search) return true;
    const s = search.toLowerCase();
    return Object.values(row).some(v => v != null && String(v).toLowerCase().includes(s));
  });
  const sorted = sortCol
    ? [...filtered].sort((a, b) => {
        const av = a[sortCol], bv = b[sortCol];
        const cmp = av == null ? -1 : bv == null ? 1 : String(av).localeCompare(String(bv), undefined, { numeric: true });
        return sortDir === "asc" ? cmp : -cmp;
      })
    : filtered;

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortDir(d => (d === "asc" ? "desc" : "asc"));
    else { setSortCol(col); setSortDir("asc"); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white w-full max-w-4xl mx-4 max-h-[85vh] flex flex-col shadow-2xl" style={{ borderRadius: 0 }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0" style={{ background: "#19105B" }}>
          <h2 className="text-sm font-bold text-white">{data?.title ?? "Loading..."}</h2>
          <button onClick={onClose} className="w-7 h-7 flex items-center justify-center text-white opacity-70 hover:opacity-100"><X className="w-4 h-4" /></button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-400"><Loader2 className="w-5 h-5 animate-spin" /></div>
        ) : data ? (
          <div className="flex-1 overflow-y-auto">
            {/* Explanation */}
            <div className="px-6 py-3 border-b border-gray-50" style={{ background: "#19105B08" }}>
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1">How this is calculated</p>
              <p className="text-xs leading-relaxed" style={{ color: "#19105B" }}>{data.explanation}</p>
            </div>

            {/* Search + column filters */}
            <div className="px-6 pt-4 flex flex-wrap items-center gap-2">
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search all columns…"
                className="text-xs px-3 py-1.5 border border-gray-200 rounded-lg flex-1 min-w-[160px] outline-none focus:border-gray-400"
                style={{ color: "#19105B" }}
              />
              {data.columns.map(col => {
                const values = Array.from(new Set(rows.map(r => (r[col] != null ? String(r[col]) : "")).filter(v => v !== ""))).sort();
                if (values.length < 2) return null;
                return (
                  <select
                    key={col}
                    value={colFilters[col] ?? ""}
                    onChange={e => setColFilters(f => ({ ...f, [col]: e.target.value }))}
                    className="text-[11px] px-2 py-1.5 border border-gray-200 rounded-lg outline-none"
                    style={{ color: "#19105B" }}
                  >
                    <option value="">{col.replace(/_/g, " ")}: All</option>
                    {values.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                );
              })}
            </div>

            {/* Data table */}
            <div className="px-6 py-4 overflow-x-auto">
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">Raw Data ({sorted.length} of {rows.length} rows)</p>
              <table className="w-full text-[11px] border-collapse">
                <thead>
                  <tr style={{ background: "#19105B", color: "#fff" }}>
                    {data.columns.map(col => (
                      <th key={col} className="px-3 py-2 text-left font-semibold cursor-pointer select-none hover:opacity-80" onClick={() => toggleSort(col)}>
                        {col.replace(/_/g, " ")}{sortCol === col ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((row, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                      {data.columns.map(col => (
                        <td key={col} className="px-3 py-1.5" style={{ color: "#19105B" }}>
                          {row[col] != null ? String(row[col]) : "-"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {sorted.length === 0 && <p className="text-xs text-gray-400 text-center py-8">No matching rows</p>}
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-12">No data</p>
        )}
      </div>
    </div>
  );
}

function ChartHeader({ title, subtitle, chart, onDrillDown }: { title: string; subtitle: string; chart: string; onDrillDown: (c: string) => void }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div>
        <h3 className="text-xs font-bold" style={{ color: "#19105B" }}>{title}</h3>
        <p className="text-[10px] text-gray-400">{subtitle}</p>
      </div>
      <button onClick={() => onDrillDown(chart)} className="w-6 h-6 rounded flex items-center justify-center hover:bg-gray-100 transition-all" title="View details">
        <Info className="w-3.5 h-3.5 text-gray-400" />
      </button>
    </div>
  );
}

export default function Dashboard() {
  const { data, isLoading } = useDashboardSummary();
  const { data: charts } = useDashboardCharts();
  const { data: dataHealth } = useDataHealth();
  const [drillDown, setDrillDown] = useState<DrillTarget | null>(null);
  const [dashTab, setDashTab] = useState<"overview" | "data-health">("overview");

  if (isLoading || !data)
    return (
      <div className="flex-1 flex items-center justify-center gap-3 text-gray-400">
        <Clock className="w-5 h-5 animate-pulse text-violet-400" />
        <span className="text-sm">Loading dashboard…</span>
      </div>
    );

  const greenProjects = data.active_projects - data.red_projects - data.amber_projects;
  const utilData = [
    { name: "Billable", value: data.billable_count, color: "#19105B" },
    { name: "Unbillable", value: data.unbillable_count, color: "#FF6196" },
    { name: "Over-Allocated", value: data.over_allocated_count, color: "#dc2626" },
  ];
  const ragData = [
    { name: "RED", value: data.red_projects, color: "#f87171" },
    { name: "AMBER", value: data.amber_projects, color: "#fbbf24" },
    { name: "GREEN", value: greenProjects, color: "#6ee7b7" },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 py-5 bg-white border-b border-gray-100 flex items-end justify-between shrink-0">
        <div>
          <h1 className="text-xl font-bold" style={{ color: "#19105B", fontFamily: "Arial, sans-serif" }}>Dashboard</h1>
          <p className="text-sm mt-0.5" style={{ color: "#19105B80", fontFamily: "Arial, sans-serif" }}>{data.total_employees.toLocaleString()} employees across Jman Group</p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Live
        </div>
      </div>

      {/* Tabs */}
      <div className="px-6 pt-4 shrink-0">
        <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl w-fit">
          <button onClick={() => setDashTab("overview")}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
              dashTab === "overview" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}>
            <TrendingUp className="w-3.5 h-3.5" /> Overview
          </button>
          <button onClick={() => setDashTab("data-health")}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
              dashTab === "data-health" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}>
            <Activity className="w-3.5 h-3.5" /> Data Health
            {dataHealth && dataHealth.overall_score < 75 && (
              <span className="ml-1 w-5 h-5 rounded-full text-[10px] font-bold flex items-center justify-center text-white" style={{ background: dataHealth.overall_score >= 50 ? "#A16BDB" : "#FF6196" }}>{dataHealth.overall_score}</span>
            )}
          </button>
        </div>
      </div>

      {dashTab === "overview" && (
      <div className="p-6 overflow-y-auto flex-1 space-y-6">
        {/* Alert */}
        {(data.red_projects > 0 || data.on_bench > 20) && (
          <div className="rounded-2xl p-4 flex items-center gap-3 bg-red-50 border border-red-100">
            <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
            <span className="text-sm text-gray-900">
              {data.red_projects > 0 && <><strong>{data.red_projects}</strong> red projects need review. </>}
              {data.on_bench > 20 && <><strong>{data.on_bench}</strong> on bench - check pipeline alignment.</>}
            </span>
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Active Employees", value: data.active_employees.toLocaleString(), icon: Users, accent: "#19105B", kpi: "active_employees" },
            { label: "On Bench", value: data.on_bench.toLocaleString(), icon: Users, accent: "#19105B", kpi: "on_bench" },
            { label: "Open Pipeline", value: data.pipeline_requests.toLocaleString(), icon: TrendingUp, accent: "#19105B", kpi: "open_pipeline" },
            { label: "Active Projects", value: data.active_projects.toLocaleString(), icon: FolderKanban, accent: "#19105B", kpi: "active_projects" },
          ].map(k => (
            <button key={k.label} onClick={() => setDrillDown({ chart: k.kpi })} className="text-left bg-white rounded-2xl p-4 border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">{k.label}</p>
                <k.icon className="w-4 h-4" style={{ color: k.accent }} />
              </div>
              <p className="text-3xl font-bold tabular-nums text-gray-900">{k.value}</p>
            </button>
          ))}
        </div>

        {/* Revenue Leakage Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <button onClick={() => setDrillDown({ chart: "unbillable" })} className="text-left bg-white rounded-2xl p-5 border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Unbillable Revenue Leakage</p>
              <PoundSterling className="w-4 h-4" style={{ color: "#FF6196" }} />
            </div>
            <p className="text-2xl font-bold tabular-nums" style={{ color: "#FF6196" }}>
              £{(data.unbillable_leakage_monthly / 1000000).toFixed(1)}M<span className="text-sm font-semibold text-gray-400">/month</span>
            </p>
            <p className="text-[10px] text-gray-400 mt-1">{data.unbillable_count} resources working but not generating revenue</p>
          </button>
          <button onClick={() => setDrillDown({ chart: "over_allocated" })} className="text-left bg-white rounded-2xl p-5 border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Over-Allocation Risk</p>
              <PoundSterling className="w-4 h-4" style={{ color: "#A16BDB" }} />
            </div>
            <p className="text-2xl font-bold tabular-nums" style={{ color: "#A16BDB" }}>
              £{(data.overalloc_leakage_monthly / 1000000).toFixed(1)}M<span className="text-sm font-semibold text-gray-400">/month</span>
            </p>
            <p className="text-[10px] text-gray-400 mt-1">{data.over_allocated_count} resources over 100% — burnout and quality risk</p>
          </button>
        </div>

        {/* Row 1: Utilization Donut + Project Health RAG + Demand vs Supply */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Allocation Health Donut */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <ChartHeader title="Allocation Health" subtitle="Billability & over-allocation visibility" chart="allocation_health" onDrillDown={(c) => setDrillDown({ chart: c })} />
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={utilData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" strokeWidth={2} stroke="#fff">
                    {utilData.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => v.toLocaleString()} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap justify-center gap-3 mt-2 text-[11px]">
              {utilData.map(d => (
                <button key={d.name} onClick={() => setDrillDown({ chart: d.name === "Billable" ? "billable" : d.name === "Unbillable" ? "unbillable" : "over_allocated" })} className="flex items-center gap-1.5 hover:opacity-70 transition-opacity">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: d.color }} />
                  {d.name} ({d.value})
                </button>
              ))}
            </div>
          </div>

          {/* Project Health */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <ChartHeader title="Project Health" subtitle={`${data.active_projects} active projects`} chart="project_health" onDrillDown={(c) => setDrillDown({ chart: c })} />
            <div className="h-48 flex flex-col justify-center">
              <ResponsiveContainer width="100%" height={40}>
                <BarChart data={[{ red: data.red_projects, amber: data.amber_projects, green: greenProjects }]} layout="vertical" barSize={28}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" hide />
                  <Tooltip />
                  <Bar dataKey="red" stackId="a" fill="#f87171" radius={[8, 0, 0, 8]} />
                  <Bar dataKey="amber" stackId="a" fill="#fbbf24" />
                  <Bar dataKey="green" stackId="a" fill="#6ee7b7" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-3 gap-3 mt-6">
                {ragData.map(d => (
                  <button
                    key={d.name}
                    onClick={() => setDrillDown({ chart: "project_health", status: d.name })}
                    className="text-center p-3 rounded-xl hover:opacity-80 transition-opacity cursor-pointer"
                    style={{ background: d.color + "10" }}
                    title={`View ${d.name} projects`}
                  >
                    <p className="text-2xl font-bold" style={{ color: d.color }}>{d.value}</p>
                    <p className="text-[10px] font-semibold mt-0.5" style={{ color: d.color }}>{d.name}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Demand vs Supply */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <ChartHeader title="Demand vs Supply" subtitle="Next 6 months - roles needed vs people freeing up" chart="demand_supply" onDrillDown={(c) => setDrillDown({ chart: c })} />
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={charts?.demand_supply ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f5" />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="demand" stroke="#19105B" strokeWidth={2} dot={{ r: 3 }} name="Demand (roles)" />
                  <Line type="monotone" dataKey="supply" stroke="#FF6196" strokeWidth={2} dot={{ r: 3 }} name="Supply (freeing)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Row 2: Pipeline by Stage + Top Open Roles + COE Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Pipeline by Deal Stage */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <ChartHeader title="Pipeline by Deal Stage" subtitle="Request distribution" chart="pipeline_by_stage" onDrillDown={(c) => setDrillDown({ chart: c })} />
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts?.pipeline_by_stage ?? []} layout="vertical" margin={{ left: 0, right: 16 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="stage" tick={{ fontSize: 10 }} width={90} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#19105B" radius={[0, 6, 6, 0]} barSize={18} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Open Roles */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <ChartHeader title="Top Open Roles" subtitle="Not Resourced - highest demand" chart="top_roles" onDrillDown={(c) => setDrillDown({ chart: c })} />
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts?.top_roles ?? []} layout="vertical" margin={{ left: 0, right: 16 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="role" tick={{ fontSize: 10 }} width={120} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#FF6196" radius={[0, 6, 6, 0]} barSize={18} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* COE Distribution */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <ChartHeader title="COE Distribution" subtitle="Employees by technology domain" chart="coe_distribution" onDrillDown={(c) => setDrillDown({ chart: c })} />
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts?.coe_distribution ?? []} layout="vertical" margin={{ left: 0, right: 16 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="coe" tick={{ fontSize: 10 }} width={100} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#19105B" radius={[0, 6, 6, 0]} barSize={18} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
      )}

      {/* Data Health Tab */}
      {dashTab === "data-health" && (
      <div className="p-6 overflow-y-auto flex-1 space-y-6">
        {dataHealth ? (
          <>
            {/* Score Header */}
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 rounded-2xl flex items-center justify-center" style={{ background: dataHealth.overall_score >= 75 ? "#19105B10" : dataHealth.overall_score >= 50 ? "#A16BDB10" : "#FF619610" }}>
                <span className="text-3xl font-bold" style={{ color: dataHealth.overall_score >= 75 ? "#19105B" : dataHealth.overall_score >= 50 ? "#A16BDB" : "#FF6196" }}>{dataHealth.overall_score}%</span>
              </div>
              <div>
                <h2 className="text-sm font-bold" style={{ color: "#19105B" }}>Data Completeness Score</h2>
                <p className="text-xs text-gray-400 mt-0.5">{dataHealth.total_gaps} data gaps identified · {dataHealth.critical_gaps} critical</p>
                <p className="text-[11px] text-gray-400 mt-1">Weighted by severity: Critical ×3, High ×2, Medium ×1, Low ×0.5</p>
              </div>
            </div>

            {/* All Gaps */}
            <div className="space-y-3">
              {dataHealth.gaps.map(g => (
                <div key={g.id} className="bg-white rounded-2xl border border-gray-100 p-5 hover:border-gray-200 transition-all">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-[10px] font-bold uppercase px-2.5 py-1 rounded-full" style={{
                        background: g.severity === "critical" ? "#FF619615" : g.severity === "high" ? "#A16BDB15" : g.severity === "medium" ? "#3411A310" : "#f3f4f6",
                        color: g.severity === "critical" ? "#FF6196" : g.severity === "high" ? "#A16BDB" : "#19105B",
                      }}>{g.severity}</span>
                      <span className="text-sm font-bold" style={{ color: "#19105B" }}>{g.area}</span>
                    </div>
                    <span className="text-lg font-bold tabular-nums" style={{ color: g.pct_complete >= 75 ? "#19105B" : g.pct_complete >= 50 ? "#A16BDB" : "#FF6196" }}>{g.pct_complete.toFixed(0)}%</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden mb-3">
                    <div className="h-full rounded-full transition-all" style={{ width: `${g.pct_complete}%`, background: g.pct_complete >= 75 ? "#19105B" : g.pct_complete >= 50 ? "#A16BDB" : "#FF6196" }} />
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{g.metric}</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
                    <p className="text-[11px]"><span className="font-semibold" style={{ color: "#19105B" }}>Impact:</span> <span className="text-gray-500">{g.impact}</span></p>
                    <p className="text-[11px]"><span className="font-semibold" style={{ color: "#19105B" }}>Action:</span> <span className="text-gray-500">{g.action}</span></p>
                  </div>
                  <button onClick={() => setDrillDown({ chart: g.id })} className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 transition-all" style={{ color: "#19105B" }}>
                    View {g.count} affected →
                  </button>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="py-12 text-sm text-gray-400 flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading data health…</div>
        )}
      </div>
      )}

      {/* Drill-down modal */}
      {drillDown && <DrillDownModal target={drillDown} onClose={() => setDrillDown(null)} />}
    </div>
  );
}
