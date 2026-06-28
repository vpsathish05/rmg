"use client";
import { useDashboardSummary } from "@/lib/hooks";
import { Users, FolderKanban, TrendingUp, Sparkles, ArrowUpRight, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";

function KpiTile({ label, value, sub, accent, icon: Icon }: {
  label: string; value: number | string; sub?: string; accent: string; icon?: React.ElementType;
}) {
  return (
    <div className="bg-white rounded-2xl p-5 border border-gray-100 hover:shadow-md transition-all">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">{label}</p>
        {Icon && (
          <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: `${accent}12` }}>
            <Icon className="w-4 h-4" style={{ color: accent }} />
          </div>
        )}
      </div>
      <p className="text-4xl font-bold tabular-nums text-gray-900">
        {typeof value === "number" ? value.toLocaleString() : value}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function DomainCard({ href, icon: Icon, title, accent, stats, badge }: {
  href: string; icon: React.ElementType; title: string; accent: string;
  stats: { label: string; value: number | string; color?: string }[];
  badge?: { text: string; color: string };
}) {
  return (
    <Link href={href} className="group block">
      <div className="bg-white rounded-2xl overflow-hidden border border-gray-100 hover:border-gray-200 hover:shadow-lg transition-all duration-200 h-full">
        <div className="px-5 py-4 flex items-center justify-between border-b border-gray-50" style={{ background: `${accent}08` }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: accent }}>
              <Icon className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold text-gray-900">{title}</span>
          </div>
          <div className="flex items-center gap-2">
            {badge && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: `${badge.color}15`, color: badge.color }}>{badge.text}</span>}
            <ArrowUpRight className="w-4 h-4 text-gray-300 group-hover:text-gray-600 transition-colors" />
          </div>
        </div>
        <div className="px-5 py-4 space-y-3">
          {stats.map(({ label, value, color }) => (
            <div key={label} className="flex items-center justify-between">
              <span className="text-xs text-gray-400">{label}</span>
              <span className="text-sm font-bold tabular-nums" style={{ color: color ?? "#1f2937" }}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </Link>
  );
}


export default function Dashboard() {
  const { data, isLoading, error } = useDashboardSummary();

  if (isLoading)
    return (
      <div className="flex-1 flex items-center justify-center gap-3 text-gray-400">
        <Clock className="w-5 h-5 animate-pulse text-violet-400" />
        <span className="text-sm">Loading dashboard…</span>
      </div>
    );
  if (error || !data)
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-red-500">
        Could not load dashboard. Is the backend running on port 8000?
      </div>
    );

  const greenProjects = data.active_projects - data.red_projects - data.amber_projects;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 py-6 bg-white border-b border-gray-100">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-sm text-gray-400 mt-0.5">{data.total_employees.toLocaleString()} employees across JMan Group</p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Live
          </div>
        </div>
      </div>

      <div className="p-8 overflow-y-auto flex-1">
        {/* Alert */}
        {(data.red_projects > 0 || data.on_bench > 20) && (
          <div className="rounded-2xl p-4 mb-6 flex items-center gap-3 bg-red-50 border border-red-100">
            <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
            <span className="text-sm text-gray-900">
              {data.red_projects > 0 && <><strong>{data.red_projects}</strong> red projects need review. </>}
              {data.on_bench > 20 && <><strong>{data.on_bench}</strong> on bench — check pipeline alignment.</>}
            </span>
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KpiTile label="Active Employees" value={data.active_employees} sub="Currently engaged" accent="#7c3aed" icon={Users} />
          <KpiTile label="On Bench" value={data.on_bench} sub="Available for assignment" accent="#6d28d9" icon={Users} />
          <KpiTile label="Open Pipeline" value={data.pipeline_requests} sub="Pending requests" accent="#a855f7" icon={TrendingUp} />
          <KpiTile label="High Probability" value={data.high_probability_pipeline} sub="≥70% win" accent="#ec4899" icon={Sparkles} />
        </div>

        {/* Domain cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <DomainCard href="/availability" icon={Users} title="People" accent="#7c3aed"
            badge={data.on_bench > 0 ? { text: `${data.on_bench} available`, color: "#7c3aed" } : undefined}
            stats={[
              { label: "Active", value: data.active_employees.toLocaleString() },
              { label: "On Bench", value: data.on_bench.toLocaleString(), color: "#7c3aed" },
              { label: "Partially Free", value: data.partially_available.toLocaleString(), color: "#d97706" },
              { label: "Fully Allocated", value: data.fully_allocated.toLocaleString() },
            ]} />
          <DomainCard href="/projects" icon={FolderKanban} title="Projects" accent="#a855f7"
            badge={data.red_projects > 0 ? { text: `${data.red_projects} RED`, color: "#dc2626" } : undefined}
            stats={[
              { label: "Active", value: data.active_projects.toLocaleString() },
              { label: "RED", value: data.red_projects.toLocaleString(), color: data.red_projects > 0 ? "#dc2626" : undefined },
              { label: "AMBER", value: data.amber_projects.toLocaleString(), color: data.amber_projects > 0 ? "#d97706" : undefined },
              { label: "GREEN", value: greenProjects.toLocaleString(), color: "#059669" },
            ]} />
          <DomainCard href="/forecast" icon={TrendingUp} title="Pipeline" accent="#ec4899"
            badge={data.high_probability_pipeline > 0 ? { text: `${data.high_probability_pipeline} hot`, color: "#ec4899" } : undefined}
            stats={[
              { label: "Open Requests", value: data.pipeline_requests.toLocaleString() },
              { label: "High Probability", value: data.high_probability_pipeline.toLocaleString(), color: "#ec4899" },
            ]} />
        </div>
      </div>
    </div>
  );
}
