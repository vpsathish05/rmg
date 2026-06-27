"use client";
import { useDashboardSummary } from "@/lib/hooks";
import { Users, FolderKanban, TrendingUp, Sparkles, ArrowUpRight, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";

// Brand palette
const C = {
  MIDNIGHT: "#19105B",
  TRYPAN:   "#3411A3",
  ROSE:     "#FF6196",
  TURQUOISE:"#71EAE1",
  LIGHTBLUE:"#26D4F0",
  AMETHYST: "#A16BDB",
  BERRY:    "#A6265E",
  EMERALD:  "#16978E",
} as const;

// ── Hero KPI tile ──────────────────────────────────────────────────────────
function KpiTile({
  label,
  value,
  accent,
  textOnAccent,
  sub,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  accent: string;
  textOnAccent?: string;
  sub?: string;
  icon?: React.ElementType;
}) {
  // Numbers are always Midnight Blue — clear hierarchy, always readable
  return (
    <div
      className="bg-card rounded-xl p-6 flex flex-col gap-2"
      style={{
        boxShadow: "0 1px 4px rgba(25,16,91,0.07), 0 1px 2px rgba(25,16,91,0.04)",
        borderTop: `3px solid ${accent}`,
      }}
    >
      <div className="flex items-start justify-between">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          {label}
        </p>
        {Icon && (
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: `${accent}18` }}
          >
            <Icon className="w-3.5 h-3.5" style={{ color: accent }} />
          </div>
        )}
      </div>
      <p
        className="text-5xl font-black tabular-nums leading-none tracking-tight"
        style={{ color: C.MIDNIGHT }}
      >
        {typeof value === "number" ? value.toLocaleString() : value}
      </p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

// ── Domain card ────────────────────────────────────────────────────────────
function DomainCard({
  href,
  icon: Icon,
  title,
  accentColor,
  iconOnDark,
  stats,
  badge,
}: {
  href: string;
  icon: React.ElementType;
  title: string;
  accentColor: string;
  iconOnDark?: boolean;
  stats: { label: string; value: number | string; color?: string }[];
  badge?: { text: string; color: string; bg: string; border: string };
}) {
  return (
    <Link href={href} className="group block">
      <div
        className="bg-card rounded-xl overflow-hidden h-full transition-all duration-200"
        style={{
          boxShadow: "0 1px 4px rgba(25,16,91,0.07)",
          border: "1px solid #D9D9D9",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLElement).style.boxShadow =
            "0 8px 24px rgba(25,16,91,0.12), 0 2px 6px rgba(25,16,91,0.06)";
          (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
          (e.currentTarget as HTMLElement).style.borderColor = accentColor + "40";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLElement).style.boxShadow = "0 1px 4px rgba(25,16,91,0.07)";
          (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
          (e.currentTarget as HTMLElement).style.borderColor = "#D9D9D9";
        }}
      >
        {/* Colored header strip */}
        <div
          className="px-5 py-4 flex items-center justify-between"
          style={{ background: `${accentColor}12`, borderBottom: `1px solid ${accentColor}28` }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: accentColor }}
            >
              <Icon
                className="w-4 h-4"
                style={{ color: iconOnDark === false ? C.MIDNIGHT : "#fff" }}
              />
            </div>
            <span className="text-sm font-bold" style={{ color: C.MIDNIGHT }}>
              {title}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {badge && (
              <span
                className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
                style={{ background: badge.bg, color: badge.color, borderColor: badge.border }}
              >
                {badge.text}
              </span>
            )}
            <ArrowUpRight
              className="w-4 h-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              style={{ color: accentColor }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="px-5 py-4 space-y-3">
          {stats.map(({ label, value, color }) => (
            <div key={label} className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{label}</span>
              <span
                className="text-sm font-bold tabular-nums"
                style={{ color: color ?? C.MIDNIGHT }}
              >
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Link>
  );
}

// ── Attention callout ──────────────────────────────────────────────────────
function AttentionCallout({ redProjects, onBench }: { redProjects: number; onBench: number }) {
  if (redProjects === 0 && onBench < 20) return null;
  return (
    <div
      className="rounded-xl p-4 mb-6 flex flex-wrap items-center gap-4"
      style={{ background: "#FFF0F4", border: `1px solid ${C.ROSE}50`, boxShadow: `0 1px 4px ${C.ROSE}18` }}
    >
      <AlertTriangle className="w-4 h-4 shrink-0" style={{ color: C.ROSE }} />
      <span className="text-sm font-semibold" style={{ color: C.BERRY }}>Needs attention:</span>
      {redProjects > 0 && (
        <span className="text-sm" style={{ color: C.MIDNIGHT }}>
          <strong>{redProjects}</strong> red project{redProjects > 1 ? "s" : ""} require review
        </span>
      )}
      {onBench > 20 && (
        <span className="text-sm" style={{ color: C.MIDNIGHT }}>
          <strong>{onBench}</strong> people on bench — check pipeline alignment
        </span>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { data, isLoading, error } = useDashboardSummary();

  if (isLoading)
    return (
      <div className="flex-1 flex items-center justify-center gap-3 text-muted-foreground">
        <Clock className="w-5 h-5 animate-pulse" style={{ color: C.TRYPAN }} />
        <span className="text-sm">Loading dashboard…</span>
      </div>
    );
  if (error || !data)
    return (
      <div className="flex-1 flex items-center justify-center text-sm" style={{ color: C.BERRY }}>
        Could not load dashboard. Is the backend running on port 8000?
      </div>
    );

  const greenProjects = data.active_projects - data.red_projects - data.amber_projects;

  return (
    <div>
      {/* Page title banner */}
      <div
        className="px-8 py-6 bg-card border-b border-border"
        style={{ borderLeft: `4px solid ${C.TRYPAN}` }}
      >
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-xl font-black" style={{ color: C.MIDNIGHT }}>Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {data.total_employees.toLocaleString()} employees across JMan Group
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <CheckCircle2 className="w-3.5 h-3.5" style={{ color: C.EMERALD }} />
            Live · refreshed on load
          </div>
        </div>
      </div>

      <div className="p-8">
        <AttentionCallout redProjects={data.red_projects} onBench={data.on_bench} />

        {/* Hero KPI strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KpiTile
            label="Active Employees"
            value={data.active_employees}
            accent={C.MIDNIGHT}
            sub="Currently engaged"
            icon={Users}
          />
          <KpiTile
            label="On Bench"
            value={data.on_bench}
            accent={C.TRYPAN}
            sub="Available for assignment"
            icon={Users}
          />
          <KpiTile
            label="Open Pipeline"
            value={data.pipeline_requests}
            accent={C.AMETHYST}
            sub="Pending resource requests"
            icon={TrendingUp}
          />
          <KpiTile
            label="High Probability"
            value={data.high_probability_pipeline}
            accent={C.ROSE}
            sub="≥70% win probability"
            icon={Sparkles}
          />
        </div>

        {/* Domain cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
          <DomainCard
            href="/availability"
            icon={Users}
            title="People"
            accentColor={C.TRYPAN}
            badge={
              data.on_bench > 0
                ? { text: `${data.on_bench} available`, color: C.TRYPAN, bg: "#EEE9F9", border: "#C5B8EF" }
                : undefined
            }
            stats={[
              { label: "Active",          value: data.active_employees.toLocaleString() },
              { label: "On Bench",        value: data.on_bench.toLocaleString(),          color: C.TRYPAN },
              { label: "Partially Free",  value: data.partially_available.toLocaleString(), color: "#D97706" },
              { label: "Fully Allocated", value: data.fully_allocated.toLocaleString() },
            ]}
          />
          <DomainCard
            href="/projects"
            icon={FolderKanban}
            title="Projects"
            accentColor={C.AMETHYST}
            badge={
              data.red_projects > 0
                ? { text: `${data.red_projects} RED`, color: C.BERRY, bg: "#FCEDF3", border: "#F0A8C0" }
                : undefined
            }
            stats={[
              { label: "Active / Deal Won", value: data.active_projects.toLocaleString() },
              { label: "RED",   value: data.red_projects.toLocaleString(),   color: data.red_projects   > 0 ? C.BERRY   : undefined },
              { label: "AMBER", value: data.amber_projects.toLocaleString(), color: data.amber_projects > 0 ? "#D97706" : undefined },
              { label: "GREEN", value: greenProjects.toLocaleString(),       color: C.EMERALD },
            ]}
          />
          <DomainCard
            href="/forecast"
            icon={TrendingUp}
            title="Pipeline"
            accentColor={C.ROSE}
            badge={
              data.high_probability_pipeline > 0
                ? { text: `${data.high_probability_pipeline} hot`, color: C.BERRY, bg: "#FFF0F4", border: `${C.ROSE}50` }
                : undefined
            }
            stats={[
              { label: "Open Requests",     value: data.pipeline_requests.toLocaleString() },
              { label: "High Probability",  value: data.high_probability_pipeline.toLocaleString(), color: C.ROSE },
            ]}
          />
        </div>

        <p className="text-xs text-muted-foreground">
          Sourced from Neon PostgreSQL · data refreshed on page load
        </p>
      </div>
    </div>
  );
}
