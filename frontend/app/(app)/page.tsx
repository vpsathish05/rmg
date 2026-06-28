"use client";
import { useDashboardSummary, useDashboardCharts } from "@/lib/hooks";
import { Users, FolderKanban, TrendingUp, Sparkles, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip,
  LineChart, Line, CartesianGrid, Legend,
} from "recharts";

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

export default function Dashboard() {
  const { data, isLoading } = useDashboardSummary();
  const { data: charts } = useDashboardCharts();

  if (isLoading || !data)
    return (
      <div className="flex-1 flex items-center justify-center gap-3 text-gray-400">
        <Clock className="w-5 h-5 animate-pulse text-violet-400" />
        <span className="text-sm">Loading dashboard…</span>
      </div>
    );

  const greenProjects = data.active_projects - data.red_projects - data.amber_projects;
  const utilData = [
    { name: "On Bench", value: data.on_bench, color: "#FF6196" },
    { name: "Partially Free", value: data.partially_available, color: "#19105B80" },
    { name: "Fully Allocated", value: data.fully_allocated, color: "#19105B" },
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
          <p className="text-sm mt-0.5" style={{ color: "#19105B80", fontFamily: "Arial, sans-serif" }}>{data.total_employees.toLocaleString()} employees across JMan Group</p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Live
        </div>
      </div>

      <div className="p-6 overflow-y-auto flex-1 space-y-6">
        {/* Alert */}
        {(data.red_projects > 0 || data.on_bench > 20) && (
          <div className="rounded-2xl p-4 flex items-center gap-3 bg-red-50 border border-red-100">
            <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
            <span className="text-sm text-gray-900">
              {data.red_projects > 0 && <><strong>{data.red_projects}</strong> red projects need review. </>}
              {data.on_bench > 20 && <><strong>{data.on_bench}</strong> on bench — check pipeline alignment.</>}
            </span>
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            { label: "Active Employees", value: data.active_employees, icon: Users, accent: "#19105B" },
            { label: "On Bench", value: data.on_bench, icon: Users, accent: "#19105B" },
            { label: "Open Pipeline", value: data.pipeline_requests, icon: TrendingUp, accent: "#19105B" },
            { label: "High Probability", value: data.high_probability_pipeline, icon: Sparkles, accent: "#FF6196" },
            { label: "Active Projects", value: data.active_projects, icon: FolderKanban, accent: "#19105B" },
          ].map(k => (
            <div key={k.label} className="bg-white rounded-2xl p-4 border border-gray-100">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">{k.label}</p>
                <k.icon className="w-4 h-4" style={{ color: k.accent }} />
              </div>
              <p className="text-3xl font-bold tabular-nums text-gray-900">{k.value.toLocaleString()}</p>
            </div>
          ))}
        </div>

        {/* Row 1: Utilization Donut + Project Health RAG + Demand vs Supply */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Utilization Donut */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Workforce Utilization</h3>
            <p className="text-[10px] text-gray-400 mb-3">{data.active_employees} active employees</p>
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
            <div className="flex justify-center gap-4 mt-2 text-[11px]">
              {utilData.map(d => (
                <span key={d.name} className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: d.color }} />
                  {d.name} ({d.value})
                </span>
              ))}
            </div>
          </div>

          {/* Project Health */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Project Health</h3>
            <p className="text-[10px] text-gray-400 mb-3">{data.active_projects} active projects</p>
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
                  <div key={d.name} className="text-center p-3 rounded-xl" style={{ background: d.color + "10" }}>
                    <p className="text-2xl font-bold" style={{ color: d.color }}>{d.value}</p>
                    <p className="text-[10px] font-semibold mt-0.5" style={{ color: d.color }}>{d.name}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Demand vs Supply */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100">
            <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Demand vs Supply</h3>
            <p className="text-[10px] text-gray-400 mb-3">Next 6 months — roles needed vs people freeing up</p>
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
            <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Pipeline by Deal Stage</h3>
            <p className="text-[10px] text-gray-400 mb-3">Request distribution</p>
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
            <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>Top Open Roles</h3>
            <p className="text-[10px] text-gray-400 mb-3">Not Resourced — highest demand</p>
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
            <h3 className="text-xs font-bold mb-1" style={{ color: "#19105B" }}>COE Distribution</h3>
            <p className="text-[10px] text-gray-400 mb-3">Employees by technology domain</p>
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
    </div>
  );
}
