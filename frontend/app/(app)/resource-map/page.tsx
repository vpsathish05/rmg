"use client";
import { useState, useCallback, useRef, useMemo } from "react";
import dynamic from "next/dynamic";
import { useResourceNetwork, useResourceTimeline, useEmployeeTimeline, useEmployeeSearch } from "@/lib/hooks";
import { Loader2, X, Users, Calendar, Search, Briefcase } from "lucide-react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const STATUS_COLORS: Record<string, string> = {
  BILLABLE: "#19105B",
  SHADOW: "#FF6196",
  UNBILLED: "#94A3B8",
  PROPOSED: "#d97706",
  PENDING: "#94A3B8",
};

export default function ResourceMapPage() {
  const [tab, setTab] = useState<"project" | "resource">("project");
  const { data: network, isLoading } = useResourceNetwork();
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [selectedEmployee, setSelectedEmployee] = useState<string | null>(null);
  const [empSearch, setEmpSearch] = useState("");
  const { data: timeline } = useResourceTimeline(selectedProject);
  const { data: empTimeline } = useEmployeeTimeline(selectedEmployee);
  const { data: searchResults } = useEmployeeSearch(empSearch);
  const graphRef = useRef<any>(null);

  const graphData = useMemo(() => {
    if (!network) return { nodes: [], links: [] };
    return {
      nodes: network.nodes.map(n => ({ ...n, val: Math.max(n.team_size, 4) })),
      links: network.links,
    };
  }, [network]);

  const handleNodeClick = useCallback((node: any) => {
    setSelectedProject(node.id);
  }, []);

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const size = Math.sqrt(node.val) * 3;
    const isSelected = node.id === selectedProject;
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = isSelected ? "#FF6196" : "#19105B";
    ctx.globalAlpha = isSelected ? 1 : 0.8;
    ctx.fill();
    ctx.globalAlpha = 1;
    if (globalScale > 1.5) {
      ctx.font = `${10 / globalScale}px Arial`;
      ctx.fillStyle = "#19105B";
      ctx.textAlign = "center";
      ctx.fillText(node.client, node.x, node.y + size + 10 / globalScale);
    }
  }, [selectedProject]);

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const start = link.source;
    const end = link.target;
    if (!start.x || !end.x) return;
    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.strokeStyle = "#19105B20";
    ctx.lineWidth = Math.min(link.shared * 0.5, 3);
    ctx.stroke();
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="px-8 py-5 bg-white border-b border-gray-100 shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ color: "#19105B" }}>Resource Map</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            {tab === "project" ? `${network?.nodes.length ?? 0} projects · ${network?.links.length ?? 0} connections` : "Employee project journey — past, present & future"}
          </p>
        </div>
        <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl">
          <button onClick={() => setTab("project")}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${tab === "project" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}>
            <Briefcase className="w-3.5 h-3.5" /> Project
          </button>
          <button onClick={() => setTab("resource")}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${tab === "resource" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}>
            <Users className="w-3.5 h-3.5" /> Resource
          </button>
        </div>
      </div>

      {tab === "project" ? (
        <div className="flex flex-1 min-h-0">
          <div className="flex-1 relative bg-gray-50">
            {isLoading ? (
              <div className="flex items-center justify-center h-full gap-2 text-gray-400">
                <Loader2 className="w-5 h-5 animate-spin" /> Loading network…
              </div>
            ) : (
              <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                nodeCanvasObject={nodeCanvasObject}
                linkCanvasObject={linkCanvasObject}
                onNodeClick={handleNodeClick}
                nodeLabel={(node: any) => `${node.id}\n${node.client} · ${node.team_size} people`}
                cooldownTicks={100}
                width={typeof window !== "undefined" ? window.innerWidth - 220 - (selectedProject ? 420 : 0) : 800}
                height={typeof window !== "undefined" ? window.innerHeight - 120 : 600}
              />
            )}
          </div>
          {selectedProject && (
            <div className="w-[420px] border-l border-gray-100 bg-white overflow-y-auto shrink-0">
              <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-4 flex items-center justify-between z-10">
                <div>
                  <p className="text-sm font-bold" style={{ color: "#19105B" }}>{timeline?.project?.id ?? selectedProject}</p>
                  <p className="text-[10px] text-gray-400">{timeline?.project?.client} · {timeline?.project?.coe ?? "—"}</p>
                </div>
                <button onClick={() => setSelectedProject(null)} className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-gray-100">
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>
              {timeline?.project && (
                <div className="px-5 py-3 border-b border-gray-50 flex items-center gap-4 text-[11px] text-gray-500">
                  <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{timeline.project.start} → {timeline.project.end}</span>
                  <span className="flex items-center gap-1"><Users className="w-3 h-3" />{timeline.resources.length} resources</span>
                </div>
              )}
              {timeline?.project && timeline.resources.length > 0 ? (
                <ProjectGantt project={timeline.project} resources={timeline.resources} />
              ) : timeline && timeline.resources.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-12">No allocations found</p>
              ) : (
                <div className="flex items-center justify-center py-12 text-gray-400"><Loader2 className="w-4 h-4 animate-spin" /></div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Resource Tab */
        <div className="flex flex-1 min-h-0">
          <div className="flex-1 p-6 overflow-y-auto">
            {/* Search */}
            <div className="max-w-md mb-6 relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input value={empSearch} onChange={e => { setEmpSearch(e.target.value); setSelectedEmployee(null); }}
                placeholder="Search employee by ID or name…"
                className="w-full pl-9 pr-3 py-2.5 text-xs rounded-xl bg-white border border-gray-200 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-200" style={{ color: "#19105B" }} />
            </div>

            {/* Search Results */}
            {empSearch.length >= 2 && searchResults && !selectedEmployee && (
              <div className="max-w-md space-y-1 mb-6">
                {searchResults.map(e => (
                  <button key={e.id} onClick={() => { setSelectedEmployee(e.id); setEmpSearch(e.job_name ?? e.id); }}
                    className="w-full text-left px-4 py-3 rounded-xl border border-gray-100 hover:border-gray-200 bg-white transition-all flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold text-white" style={{ background: "#19105B" }}>
                      {(e.job_name ?? e.id).slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-xs font-semibold" style={{ color: "#19105B" }}>{e.job_name ?? e.id}</p>
                      <p className="text-[10px] text-gray-400">{e.id} · {e.role ?? "—"}</p>
                    </div>
                  </button>
                ))}
                {searchResults.length === 0 && <p className="text-xs text-gray-400 px-4">No employees found</p>}
              </div>
            )}

            {/* Employee Timeline */}
            {selectedEmployee && empTimeline?.employee && (
              <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-50">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ background: "#19105B" }}>
                      {(empTimeline.employee.job_name ?? empTimeline.employee.id).slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-bold" style={{ color: "#19105B" }}>{empTimeline.employee.job_name ?? empTimeline.employee.id}</p>
                      <p className="text-[10px] text-gray-400">{empTimeline.employee.id} · {empTimeline.employee.canonical_role ?? "—"} · {empTimeline.employee.location ?? ""}</p>
                    </div>
                  </div>
                </div>
                <div className="px-5 py-4">
                  <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Project Journey (6 months back → 6 months forward)</p>
                  <EmployeeGantt allocations={empTimeline.allocations} />
                </div>
              </div>
            )}

            {!selectedEmployee && empSearch.length < 2 && (
              <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                <Users className="w-10 h-10 mb-3 opacity-30" />
                <p className="text-sm font-medium">Search for an employee</p>
                <p className="text-xs mt-1">See their full project journey — past, current & future</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


function ProjectGantt({ project, resources }: {
  project: { start: string | null; end: string | null };
  resources: { employee_id: string; job_name: string | null; canonical_role: string | null; start_date: string | null; end_date: string | null; allocation_pct: number | null; status: string | null }[];
}) {
  const projStart = project.start ? new Date(project.start).getTime() : Date.now();
  const projEnd = project.end ? new Date(project.end).getTime() : Date.now();
  const span = Math.max(projEnd - projStart, 1);

  return (
    <div className="px-5 py-4 space-y-1.5">
      {/* Project bar */}
      <div className="mb-4">
        <div className="h-2 rounded-full w-full" style={{ background: "#19105B20" }} />
        <div className="flex justify-between text-[9px] text-gray-400 mt-1">
          <span>{project.start?.slice(0, 7)}</span>
          <span>{project.end?.slice(0, 7)}</span>
        </div>
      </div>

      {/* Resource bars */}
      {resources.map((r, i) => {
        const rStart = r.start_date ? new Date(r.start_date).getTime() : projStart;
        const rEnd = r.end_date ? new Date(r.end_date).getTime() : projEnd;
        const left = Math.max(0, ((rStart - projStart) / span) * 100);
        const width = Math.min(100 - left, Math.max(2, ((rEnd - rStart) / span) * 100));
        const color = STATUS_COLORS[r.status ?? ""] ?? "#94A3B8";

        return (
          <div key={`${r.employee_id}-${i}`} className="flex items-center gap-2">
            <div className="w-[110px] shrink-0 truncate">
              <p className="text-[10px] font-semibold truncate" style={{ color: "#19105B" }}>{r.job_name ?? r.employee_id}</p>
              <p className="text-[9px] text-gray-400 truncate">{r.canonical_role ?? ""}</p>
            </div>
            <div className="flex-1 h-5 relative bg-gray-50 rounded">
              <div
                className="absolute top-0.5 bottom-0.5 rounded"
                style={{ left: `${left}%`, width: `${width}%`, background: color, opacity: 0.85 }}
              />
            </div>
            <span className="text-[9px] text-gray-400 w-8 text-right shrink-0">{r.allocation_pct ?? "—"}%</span>
          </div>
        );
      })}

      {/* Legend */}
      <div className="flex gap-3 pt-3 border-t border-gray-50 mt-3">
        {Object.entries(STATUS_COLORS).map(([k, v]) => (
          <span key={k} className="flex items-center gap-1 text-[9px] text-gray-400">
            <span className="w-2 h-2 rounded-sm" style={{ background: v }} />{k}
          </span>
        ))}
      </div>
    </div>
  );
}



function EmployeeGantt({ allocations }: {
  allocations: { project_id: string; client: string; coe: string | null; start_date: string | null; end_date: string | null; allocation_pct: number | null; status: string | null; project_status: string | null }[];
}) {
  if (!allocations.length) return <p className="text-xs text-gray-400 text-center py-8">No allocations in this period</p>;

  const now = Date.now();
  const sixMonthsBack = now - 6 * 30 * 24 * 60 * 60 * 1000;
  const sixMonthsFwd = now + 6 * 30 * 24 * 60 * 60 * 1000;
  const span = sixMonthsFwd - sixMonthsBack;
  const todayPct = ((now - sixMonthsBack) / span) * 100;

  return (
    <div className="space-y-2">
      {/* Time axis */}
      <div className="relative h-4 mb-2">
        <div className="absolute left-0 right-0 top-1/2 h-px bg-gray-200" />
        <div className="absolute top-0 bottom-0 w-px" style={{ left: `${todayPct}%`, background: "#FF6196" }} />
        <span className="absolute text-[8px] font-bold" style={{ left: `${todayPct}%`, top: -2, transform: "translateX(-50%)", color: "#FF6196" }}>TODAY</span>
        <span className="absolute left-0 bottom-0 text-[8px] text-gray-400">-6m</span>
        <span className="absolute right-0 bottom-0 text-[8px] text-gray-400">+6m</span>
      </div>

      {/* Allocation bars */}
      {allocations.map((a, i) => {
        const aStart = a.start_date ? new Date(a.start_date).getTime() : sixMonthsBack;
        const aEnd = a.end_date ? new Date(a.end_date).getTime() : sixMonthsFwd;
        const left = Math.max(0, ((Math.max(aStart, sixMonthsBack) - sixMonthsBack) / span) * 100);
        const right = Math.min(100, ((Math.min(aEnd, sixMonthsFwd) - sixMonthsBack) / span) * 100);
        const width = Math.max(2, right - left);
        const color = STATUS_COLORS[a.status ?? ""] ?? "#94A3B8";
        const isCurrent = aStart <= now && (aEnd >= now || !a.end_date);

        return (
          <div key={`${a.project_id}-${i}`} className="flex items-center gap-2">
            <div className="w-[100px] shrink-0 truncate">
              <p className="text-[10px] font-semibold truncate" style={{ color: isCurrent ? "#19105B" : "#6b7280" }}>{a.client}</p>
              <p className="text-[9px] text-gray-400 truncate">{a.project_id}</p>
            </div>
            <div className="flex-1 h-6 relative bg-gray-50 rounded">
              <div className="absolute top-0 bottom-0 w-px" style={{ left: `${todayPct}%`, background: "#FF619640" }} />
              <div
                className="absolute top-1 bottom-1 rounded"
                style={{ left: `${left}%`, width: `${width}%`, background: color, opacity: isCurrent ? 1 : 0.5 }}
              />
            </div>
            <span className="text-[9px] text-gray-400 w-8 text-right shrink-0">{a.allocation_pct ?? "—"}%</span>
          </div>
        );
      })}

      {/* Legend */}
      <div className="flex gap-3 pt-3 border-t border-gray-50 mt-3">
        {Object.entries(STATUS_COLORS).map(([k, v]) => (
          <span key={k} className="flex items-center gap-1 text-[9px] text-gray-400">
            <span className="w-2 h-2 rounded-sm" style={{ background: v }} />{k}
          </span>
        ))}
        <span className="flex items-center gap-1 text-[9px] ml-auto" style={{ color: "#FF6196" }}>
          <span className="w-px h-3" style={{ background: "#FF6196" }} /> Today
        </span>
      </div>
    </div>
  );
}
