"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Sparkles, Loader2, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

interface RoleCode { raw_code: string; canonical_roles: string[] | null; always_best_match: boolean }
interface ScoreBreakdown { skill: number; competency: number | null; availability: number; productivity: number; total: number; has_competency: boolean }
interface Candidate { employee_id: string; job_name: string | null; canonical_role: string | null; location: string | null; department_name: string | null; current_allocated_pct: number; available_pct: number; category: string; scores: ScoreBreakdown; rationale: string | null }
interface Summary { total_evaluated: number; role_matched: number; available: number; best_match: number; stretch: number; no_resource: boolean; hire_signal: string | null }
interface RecommendResult { candidates: Candidate[]; summary: Summary; role_info: { raw_code: string; canonical_roles: string[] | null } | null }

const CATEGORY_STYLE: Record<string, string> = {
  Available: "bg-emerald-50 text-emerald-700 border-emerald-200",
  BestMatch: "bg-sky-50 text-sky-700 border-sky-200",
  Stretch:   "bg-muted text-muted-foreground border-border",
};

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex items-center gap-2 min-w-[72px]">
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${Math.round(value * 100)}%`, background: color }} />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground w-7 text-right">{Math.round(value * 100)}%</span>
    </div>
  );
}

function CandidateRow({ c, rank }: { c: Candidate; rank: number }) {
  const [open, setOpen] = useState(false);
  const s = c.scores;
  return (
    <>
      <TableRow className="hover:bg-muted/30">
        <TableCell className="text-xs text-muted-foreground tabular-nums">{rank}</TableCell>
        <TableCell className="font-mono text-xs text-muted-foreground">{c.employee_id}</TableCell>
        <TableCell className="text-sm">{c.job_name ?? "—"}</TableCell>
        <TableCell className="text-xs text-muted-foreground">{c.location ?? "—"}</TableCell>
        <TableCell className="text-center tabular-nums text-sm">
          <span style={{ color: c.available_pct > 0 ? "#3411A3" : undefined }} className={c.available_pct > 0 ? "font-semibold" : "text-muted-foreground"}>
            {c.available_pct.toFixed(0)}%
          </span>
        </TableCell>
        <TableCell>
          <Badge variant="outline" className={`text-xs ${CATEGORY_STYLE[c.category] ?? CATEGORY_STYLE.Stretch}`}>
            {c.category === "BestMatch" ? "Best Match" : c.category}
          </Badge>
        </TableCell>
        <TableCell className="w-28"><ScoreBar value={s.total}        color="#3411A3" /></TableCell>
        <TableCell className="w-24"><ScoreBar value={s.skill}        color="#3B82F6" /></TableCell>
        <TableCell className="w-24">
          {s.competency != null
            ? <ScoreBar value={s.competency} color="#F59E0B" />
            : <span className="text-xs text-muted-foreground/40">—</span>}
        </TableCell>
        <TableCell className="w-24"><ScoreBar value={s.availability} color="#10B981" /></TableCell>
        <TableCell className="w-24"><ScoreBar value={s.productivity} color="#F97316" /></TableCell>
        <TableCell className="w-8">
          {c.rationale && (
            <button onClick={() => setOpen(v => !v)} className="text-muted-foreground hover:text-foreground">
              {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          )}
        </TableCell>
      </TableRow>
      {open && c.rationale && (
        <TableRow style={{ background: "rgba(10,181,166,0.04)" }}>
          <TableCell />
          <TableCell colSpan={11} className="py-3 pb-4">
            <div className="flex gap-2.5 items-start">
              <Sparkles className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: "#3411A3" }} />
              <p className="text-sm text-foreground leading-relaxed">{c.rationale}</p>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function RecommendPageInner() {
  const params = useSearchParams();
  const [roleCode, setRoleCode] = useState(params.get("role_code") ?? "");
  const [coe, setCoe] = useState(params.get("coe") ?? "");
  const [allocPct, setAllocPct] = useState(Number(params.get("allocation") ?? 100));
  const [durationWeeks, setDurationWeeks] = useState(params.get("weeks") ?? "");
  const [skillsRequired, setSkillsRequired] = useState(params.get("skills") ?? "");

  const { data: roleCodes = [] } = useQuery<RoleCode[]>({
    queryKey: ["role-codes"],
    queryFn: () => api.get("/api/recommend/role-codes").then(r => r.data),
  });
  const { data: coes = [] } = useQuery<string[]>({
    queryKey: ["coes"],
    queryFn: () => api.get("/api/recommend/coes").then(r => r.data),
  });

  const mutation = useMutation<RecommendResult, Error, void>({
    mutationFn: () =>
      api.post("/api/recommend?with_rationale=true", {
        role_code: roleCode, coe, allocation_pct: allocPct,
        duration_weeks: durationWeeks ? Number(durationWeeks) : undefined,
        skills_required: skillsRequired || undefined,
      }).then(r => r.data),
  });

  const result = mutation.data;
  const candidates = result?.candidates ?? [];
  const summary = result?.summary;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Find Candidates"
        subtitle="Scored by skill (40%), competency (25%), availability (25%), productivity (10%)"
      />

      <div className="p-8">
        {/* Request form */}
        <div className="bg-card border border-border rounded-lg p-6 mb-8">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Resource Request</p>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
            <div className="lg:col-span-2">
              <label className="text-xs font-medium text-foreground mb-1.5 block">Role code *</label>
              <Select value={roleCode} onValueChange={v => setRoleCode(v ?? "")}>
                <SelectTrigger className="bg-background"><SelectValue placeholder="Select role…" /></SelectTrigger>
                <SelectContent>
                  {roleCodes.map(r => (
                    <SelectItem key={r.raw_code} value={r.raw_code}>
                      {r.raw_code}
                      {r.canonical_roles && <span className="text-muted-foreground ml-1.5 text-xs">({r.canonical_roles[0]}{r.canonical_roles.length > 1 ? " +more" : ""})</span>}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="lg:col-span-2">
              <label className="text-xs font-medium text-foreground mb-1.5 block">Technology / COE *</label>
              <Select value={coe} onValueChange={v => setCoe(v ?? "")}>
                <SelectTrigger className="bg-background"><SelectValue placeholder="Select COE…" /></SelectTrigger>
                <SelectContent>{coes.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-xs font-medium text-foreground mb-1.5 block">Allocation %</label>
              <Input type="number" min={10} max={100} step={10} value={allocPct} onChange={e => setAllocPct(Number(e.target.value))} className="bg-background" />
            </div>

            <div>
              <label className="text-xs font-medium text-foreground mb-1.5 block">Duration (weeks)</label>
              <Input type="number" min={1} placeholder="Optional" value={durationWeeks} onChange={e => setDurationWeeks(e.target.value)} className="bg-background" />
            </div>

            <div className="lg:col-span-4">
              <label className="text-xs font-medium text-foreground mb-1.5 block">Skills required (optional)</label>
              <Input placeholder="e.g. Python, Spark, SQL…" value={skillsRequired} onChange={e => setSkillsRequired(e.target.value)} className="bg-background" />
            </div>

            <div className="lg:col-span-2 flex items-end">
              <Button className="w-full" disabled={!roleCode || !coe || mutation.isPending} onClick={() => mutation.mutate()}>
                {mutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Scoring…</> : <><Sparkles className="w-4 h-4 mr-2" />Find Candidates</>}
              </Button>
            </div>
          </div>
        </div>

        {mutation.isError && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/8 border border-destructive/20 text-destructive text-sm flex gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />{mutation.error.message}
          </div>
        )}

        {result && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {[
                { label: "Evaluated",             value: summary?.total_evaluated ?? 0, teal: false },
                { label: "Available now",          value: summary?.available ?? 0,       teal: true },
                { label: "Best Match (allocated)", value: summary?.best_match ?? 0,      teal: false },
                { label: "Stretch",                value: summary?.stretch ?? 0,         teal: false },
              ].map(({ label, value, teal }) => (
                <Card key={label} className="border-border">
                  <CardContent className="px-5 py-4">
                    <p className="text-xs text-muted-foreground mb-1">{label}</p>
                    <p className="text-2xl font-bold tabular-nums" style={teal ? { color: "#3411A3" } : undefined}>{value}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {summary?.hire_signal && (
              <div className="mb-4 p-4 rounded-lg border" style={{ background: "rgba(239,68,68,0.05)", borderColor: "rgba(239,68,68,0.25)" }}>
                <div className="flex gap-2.5 items-start">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
                  <div>
                    <p className="text-sm font-semibold text-red-700 mb-0.5">External hire recommended</p>
                    <p className="text-sm text-red-600">{summary.hire_signal}</p>
                  </div>
                </div>
              </div>
            )}
            {!summary?.hire_signal && summary?.no_resource && (
              <div className="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm flex gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                No candidates with sufficient availability. Results show closest available options.
              </div>
            )}

            {result.role_info && (
              <p className="text-xs text-muted-foreground mb-3">
                <span className="font-medium text-foreground">{result.role_info.raw_code}</span>
                {" → "}{result.role_info.canonical_roles?.join(", ") ?? "—"}
                {" · "}{candidates.length} candidates · AI rationale for top 10
              </p>
            )}

            <div className="rounded-lg border border-border bg-card overflow-hidden overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50 hover:bg-muted/50">
                    <TableHead className="w-8 text-xs">#</TableHead>
                    <TableHead className="text-xs">ID</TableHead>
                    <TableHead className="text-xs">Role</TableHead>
                    <TableHead className="text-xs">Location</TableHead>
                    <TableHead className="text-center text-xs">Available</TableHead>
                    <TableHead className="text-xs">Category</TableHead>
                    <TableHead className="text-xs">Total ▾</TableHead>
                    <TableHead className="text-xs">Skill 40%</TableHead>
                    <TableHead className="text-xs">Comp 25%</TableHead>
                    <TableHead className="text-xs">Avail 25%</TableHead>
                    <TableHead className="text-xs">Prod 10%</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {candidates.length === 0 && (
                    <TableRow><TableCell colSpan={12} className="text-center py-10 text-muted-foreground text-sm">No candidates found.</TableCell></TableRow>
                  )}
                  {candidates.map((c, i) => <CandidateRow key={c.employee_id} c={c} rank={i + 1} />)}
                </TableBody>
              </Table>
            </div>
          </>
        )}

        {!result && !mutation.isPending && (
          <div className="text-center py-20 text-muted-foreground">
            <Sparkles className="w-8 h-8 mx-auto mb-3 opacity-25" />
            <p className="text-sm">Select a role and COE, then click Find Candidates.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function RecommendPage() {
  return <Suspense><RecommendPageInner /></Suspense>;
}
