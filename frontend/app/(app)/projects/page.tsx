"use client";
import { useState, useMemo } from "react";
import { useProjectHealth, useOverrunningProjects, useRampDownProjects } from "@/lib/hooks";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { AlertTriangle, Clock } from "lucide-react";

const RAG_STYLE: Record<string, string> = {
  RED:      "bg-red-50 text-red-700 border-red-200",
  AMBER:    "bg-amber-50 text-amber-700 border-amber-200",
  GREEN:    "bg-emerald-50 text-emerald-700 border-emerald-200",
  NO_COLOR: "bg-muted text-muted-foreground border-border",
};

function RagBadge({ value }: { value: string | null }) {
  const v = value ?? "NO_COLOR";
  return (
    <Badge variant="outline" className={`text-xs ${RAG_STYLE[v] ?? RAG_STYLE.NO_COLOR}`}>
      {v === "NO_COLOR" ? "—" : v}
    </Badge>
  );
}

const HEALTH_FILTERS = ["RED", "AMBER", "GREEN", "NO_COLOR"] as const;

function AlertPanel({
  title,
  icon,
  accentClass,
  items,
  emptyText,
  renderItem,
}: {
  title: string;
  icon: React.ReactNode;
  accentClass: string;
  items: unknown[] | undefined;
  emptyText: string;
  renderItem: (item: unknown, i: number) => React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  if (!items || items.length === 0) return null;
  return (
    <div className={`mb-6 rounded-lg border ${accentClass} overflow-hidden`}>
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        onClick={() => setCollapsed((v) => !v)}
      >
        <div className="flex items-center gap-2 text-sm font-semibold">
          {icon}
          {title}
          <span className="ml-1 tabular-nums font-bold">({items.length})</span>
        </div>
        <span className="text-xs text-muted-foreground">{collapsed ? "Show" : "Hide"}</span>
      </button>
      {!collapsed && (
        <div className="overflow-x-auto border-t border-inherit">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-inherit bg-black/[0.02]">
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Project</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Client</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">COE</th>
                <th className="text-right px-4 py-2 font-medium text-muted-foreground">End Date</th>
                <th className="text-right px-4 py-2 font-medium text-muted-foreground">Days</th>
                <th className="text-right px-4 py-2 font-medium text-muted-foreground">Headcount</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => renderItem(item, i))}
              {items.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-4 text-center text-muted-foreground">{emptyText}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ProjectsPage() {
  const [search, setSearch] = useState("");
  const [healthFilter, setHealthFilter] = useState("all");
  const { data, isLoading, error } = useProjectHealth();
  const { data: overrunning } = useOverrunningProjects();
  const { data: rampDown } = useRampDownProjects(60);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.filter((p) => {
      const q = search.toLowerCase();
      const matchSearch =
        !search ||
        p.project_id.toLowerCase().includes(q) ||
        p.client_id.toLowerCase().includes(q) ||
        (p.proposition_coe ?? "").toLowerCase().includes(q);
      return matchSearch && (healthFilter === "all" || p.overall_health === healthFilter);
    });
  }, [data, search, healthFilter]);

  const healthCounts = useMemo(() => {
    if (!data) return {} as Record<string, number>;
    return Object.fromEntries(HEALTH_FILTERS.map((h) => [h, data.filter((p) => p.overall_health === h).length]));
  }, [data]);

  if (isLoading) return <div className="p-8 text-sm text-muted-foreground">Loading project health…</div>;
  if (error)    return <div className="p-8 text-sm text-destructive">Failed to load project health data.</div>;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Project Health"
        subtitle={`${data?.length} active & deal-won projects · ${filtered.length} matching`}
      />

      <div className="p-8">
        {/* Overrunning panel */}
        <AlertPanel
          title="Overrunning Projects"
          icon={<AlertTriangle className="w-4 h-4 text-red-600" />}
          accentClass="border-red-200 bg-red-50/30"
          items={overrunning}
          emptyText="No overrunning projects."
          renderItem={(item: unknown, i) => {
            const p = item as { project_id: string; client_id: string; proposition_coe: string | null; project_end_date: string | null; days_overrun: number; headcount: number };
            return (
              <tr key={p.project_id} className={`border-t border-red-100 ${i % 2 === 1 ? "bg-red-50/20" : ""}`}>
                <td className="px-4 py-2 font-mono text-muted-foreground">{p.project_id}</td>
                <td className="px-4 py-2">{p.client_id}</td>
                <td className="px-4 py-2 text-muted-foreground">{p.proposition_coe ?? "—"}</td>
                <td className="px-4 py-2 text-right text-muted-foreground">{p.project_end_date ?? "—"}</td>
                <td className="px-4 py-2 text-right font-semibold text-red-700">{p.days_overrun}d over</td>
                <td className="px-4 py-2 text-right">{p.headcount}</td>
              </tr>
            );
          }}
        />

        {/* Ramp-down panel */}
        <AlertPanel
          title="Releasing in ≤60 Days"
          icon={<Clock className="w-4 h-4 text-amber-600" />}
          accentClass="border-amber-200 bg-amber-50/30"
          items={rampDown}
          emptyText="No projects releasing in the next 60 days."
          renderItem={(item: unknown, i) => {
            const p = item as { project_id: string; client_id: string; proposition_coe: string | null; project_end_date: string | null; days_remaining: number; headcount: number };
            return (
              <tr key={p.project_id} className={`border-t border-amber-100 ${i % 2 === 1 ? "bg-amber-50/20" : ""}`}>
                <td className="px-4 py-2 font-mono text-muted-foreground">{p.project_id}</td>
                <td className="px-4 py-2">{p.client_id}</td>
                <td className="px-4 py-2 text-muted-foreground">{p.proposition_coe ?? "—"}</td>
                <td className="px-4 py-2 text-right text-muted-foreground">{p.project_end_date ?? "—"}</td>
                <td className={`px-4 py-2 text-right font-semibold ${p.days_remaining <= 14 ? "text-red-700" : p.days_remaining <= 30 ? "text-amber-700" : "text-muted-foreground"}`}>
                  {p.days_remaining}d left
                </td>
                <td className="px-4 py-2 text-right">{p.headcount}</td>
              </tr>
            );
          }}
        />

        {/* Health chips */}
        <div className="flex flex-wrap gap-2 mb-5">
          {HEALTH_FILTERS.map((h) => (
            <button
              key={h}
              onClick={() => setHealthFilter(h === healthFilter ? "all" : h)}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-opacity ${RAG_STYLE[h]} ${healthFilter !== "all" && healthFilter !== h ? "opacity-30" : ""}`}
            >
              {h === "NO_COLOR" ? "No WSR" : h}
              <span className="tabular-nums font-semibold">{healthCounts[h] ?? 0}</span>
            </button>
          ))}
        </div>

        <div className="mb-4">
          <Input
            placeholder="Search project / client / COE…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs bg-card"
          />
        </div>

        <div className="rounded-lg border border-border bg-card overflow-hidden overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="w-36 text-xs">Project</TableHead>
                <TableHead className="w-28 text-xs">Client</TableHead>
                <TableHead className="w-24 text-xs">Status</TableHead>
                <TableHead className="text-xs">COE</TableHead>
                <TableHead className="w-24 text-xs">Overall</TableHead>
                <TableHead className="text-center text-xs">Scope</TableHead>
                <TableHead className="text-center text-xs">Schedule</TableHead>
                <TableHead className="text-center text-xs">Quality</TableHead>
                <TableHead className="text-center text-xs">CSAT</TableHead>
                <TableHead className="text-center text-xs">Team</TableHead>
                <TableHead className="w-28 text-xs">WSR Week</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow><TableCell colSpan={11} className="text-center py-10 text-muted-foreground text-sm">No projects match filters.</TableCell></TableRow>
              )}
              {filtered.map((p) => (
                <TableRow key={p.project_id} className="hover:bg-muted/30">
                  <TableCell className="font-mono text-xs text-muted-foreground">{p.project_id}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{p.client_id}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={`text-xs ${p.project_status === "ACTIVE" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-sky-50 text-sky-700 border-sky-200"}`}>
                      {p.project_status ?? "—"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{p.proposition_coe ?? "—"}</TableCell>
                  <TableCell><RagBadge value={p.overall_health} /></TableCell>
                  <TableCell className="text-center"><RagBadge value={p.scope_status} /></TableCell>
                  <TableCell className="text-center"><RagBadge value={p.schedule_status} /></TableCell>
                  <TableCell className="text-center"><RagBadge value={p.quality_status} /></TableCell>
                  <TableCell className="text-center"><RagBadge value={p.csat_status} /></TableCell>
                  <TableCell className="text-center"><RagBadge value={p.team_status} /></TableCell>
                  <TableCell className="text-xs text-muted-foreground">{p.week_end ?? "No data"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
