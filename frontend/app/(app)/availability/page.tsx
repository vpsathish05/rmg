"use client";
import { useState, useMemo } from "react";
import { useAvailability, useEmployeeAllocations } from "@/lib/hooks";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { ChevronDown, ChevronRight, Loader2 } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  "On Bench":       "bg-sky-50 text-sky-700 border-sky-200",
  "Available":      "bg-emerald-50 text-emerald-700 border-emerald-200",
  "Partial":        "bg-amber-50 text-amber-700 border-amber-200",
  "Allocated":      "bg-zinc-100 text-zinc-600 border-zinc-200",
  "Over-allocated": "bg-red-50 text-red-700 border-red-200",
};

const BILL_STYLE: Record<string, string> = {
  BILLABLE: "bg-emerald-50 text-emerald-700 border-emerald-200",
  SHADOW:   "bg-sky-50 text-sky-700 border-sky-200",
  UNBILLED: "bg-amber-50 text-amber-700 border-amber-200",
};

const ALL_STATUSES = ["On Bench", "Available", "Partial", "Allocated", "Over-allocated"];
const PAGE_SIZE = 50;

function DrillDownRow({ employeeId }: { employeeId: string }) {
  const { data, isLoading } = useEmployeeAllocations(employeeId);

  if (isLoading) {
    return (
      <TableRow style={{ background: "rgba(10,181,166,0.03)" }}>
        <TableCell colSpan={8} className="py-3 pl-10">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
        </TableCell>
      </TableRow>
    );
  }

  if (!data || data.length === 0) {
    return (
      <TableRow style={{ background: "rgba(10,181,166,0.03)" }}>
        <TableCell colSpan={8} className="py-3 pl-10 text-xs text-muted-foreground">No active allocations.</TableCell>
      </TableRow>
    );
  }

  return (
    <>
      {data.map((a, i) => (
        <TableRow key={`${a.project_id}-${i}`} style={{ background: "rgba(10,181,166,0.03)" }}>
          <TableCell />
          <TableCell className="pl-10">
            <span className="font-mono text-xs text-muted-foreground">{a.project_id}</span>
            {a.client_id && <span className="ml-2 text-xs text-muted-foreground/70">({a.client_id})</span>}
          </TableCell>
          <TableCell colSpan={2} className="text-xs text-muted-foreground">
            {a.start_date ?? "—"} → {a.is_open_ended ? "Open ended" : (a.end_date ?? "—")}
            {a.days_remaining != null && !a.is_open_ended && (
              <span className={`ml-2 font-medium ${a.days_remaining <= 14 ? "text-red-600" : a.days_remaining <= 30 ? "text-amber-600" : "text-muted-foreground"}`}>
                ({a.days_remaining}d left)
              </span>
            )}
          </TableCell>
          <TableCell className="text-right tabular-nums text-xs text-muted-foreground">
            {a.allocation_pct != null ? `${a.allocation_pct.toFixed(0)}%` : "—"}
          </TableCell>
          <TableCell />
          <TableCell>
            {a.resourcing_status && (
              <Badge variant="outline" className={`text-xs ${BILL_STYLE[a.resourcing_status.toUpperCase()] ?? "bg-muted text-muted-foreground"}`}>
                {a.resourcing_status}
              </Badge>
            )}
          </TableCell>
          <TableCell />
        </TableRow>
      ))}
    </>
  );
}

export default function AvailabilityPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const { data, isLoading, error } = useAvailability();

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.filter((e) => {
      const q = search.toLowerCase();
      const matchSearch =
        !search ||
        e.employee_id.toLowerCase().includes(q) ||
        (e.job_name ?? "").toLowerCase().includes(q) ||
        (e.department_name ?? "").toLowerCase().includes(q);
      return matchSearch && (statusFilter === "all" || e.allocation_status === statusFilter);
    });
  }, [data, search, statusFilter]);

  const statusCounts = useMemo(() => {
    if (!data) return {} as Record<string, number>;
    return Object.fromEntries(ALL_STATUSES.map((s) => [s, data.filter((e) => e.allocation_status === s).length]));
  }, [data]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const visible = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function toggleExpand(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  if (isLoading) return <div className="p-8 text-sm text-muted-foreground">Loading availability data…</div>;
  if (error)    return <div className="p-8 text-sm text-destructive">Failed to load availability data.</div>;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Availability"
        subtitle={`${data?.length?.toLocaleString()} active employees · ${filtered.length} matching`}
      />

      <div className="p-8 flex-1">
        {/* Status chips */}
        <div className="flex flex-wrap gap-2 mb-5">
          {ALL_STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s === statusFilter ? "all" : s); setPage(0); }}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-opacity ${STATUS_STYLE[s]} ${statusFilter !== "all" && statusFilter !== s ? "opacity-30" : ""}`}
            >
              {s}
              <span className="tabular-nums font-semibold">{statusCounts[s] ?? 0}</span>
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-4">
          <Input
            placeholder="Search employee / role / department…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            className="max-w-xs bg-card"
          />
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v ?? "all"); setPage(0); }}>
            <SelectTrigger className="w-44 bg-card">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {ALL_STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="w-8" />
                <TableHead className="w-32 text-xs">Employee</TableHead>
                <TableHead className="text-xs">Role</TableHead>
                <TableHead className="text-xs">Department</TableHead>
                <TableHead className="text-right w-28 text-xs">Allocated %</TableHead>
                <TableHead className="text-right w-28 text-xs">Available %</TableHead>
                <TableHead className="w-36 text-xs">Billability</TableHead>
                <TableHead className="w-36 text-xs">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.length === 0 && (
                <TableRow><TableCell colSpan={8} className="text-center py-10 text-muted-foreground text-sm">No employees match the current filters.</TableCell></TableRow>
              )}
              {visible.map((e) => {
                const isOpen = expanded.has(e.employee_id);
                const hasAllocs = e.allocated_pct > 0;
                return (
                  <>
                    <TableRow
                      key={e.employee_id}
                      className={`hover:bg-muted/30 ${hasAllocs ? "cursor-pointer" : ""}`}
                      onClick={() => hasAllocs && toggleExpand(e.employee_id)}
                    >
                      <TableCell className="w-8 text-muted-foreground">
                        {hasAllocs && (
                          isOpen
                            ? <ChevronDown className="w-3.5 h-3.5" />
                            : <ChevronRight className="w-3.5 h-3.5" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{e.employee_id}</TableCell>
                      <TableCell className="text-sm">{e.job_name ?? "—"}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{e.department_name ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums text-sm">{e.allocated_pct.toFixed(0)}%</TableCell>
                      <TableCell className="text-right tabular-nums text-sm font-semibold" style={{ color: e.available_pct > 0 ? "#3411A3" : undefined }}>
                        {e.available_pct.toFixed(0)}%
                      </TableCell>
                      <TableCell>
                        {e.billability ? (
                          <Badge variant="outline" className={`text-xs ${BILL_STYLE[e.billability] ?? "bg-muted text-muted-foreground"}`}>
                            {e.billability}
                          </Badge>
                        ) : <span className="text-xs text-muted-foreground/40">—</span>}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`text-xs ${STATUS_STYLE[e.allocation_status]}`}>
                          {e.allocation_status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                    {isOpen && <DrillDownRow employeeId={e.employee_id} />}
                  </>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 text-sm text-muted-foreground">
            <span>{page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length}</span>
            <div className="flex gap-2">
              <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border border-border rounded text-xs disabled:opacity-40 hover:bg-muted/40">← Prev</button>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} className="px-3 py-1 border border-border rounded text-xs disabled:opacity-40 hover:bg-muted/40">Next →</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
