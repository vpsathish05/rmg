"use client";
import { useState, useMemo } from "react";
import { useLifecycleTop, useResourceTimeline, useEmployeeTimeline, useEmployeeSearch } from "@/lib/hooks";
import { Loader2, Search, Users, Briefcase, Calendar, MapPin, X } from "lucide-react";

const STATUS_COLORS: Record<string, string> = { BILLABLE: "#19105B", SHADOW: "#FF6196", UNBILLED: "#94A3B8", PROPOSED: "#d97706", PENDING: "#94A3B8" };

export default function LifecyclePage() {
  const { data: top, isLoading } = useLifecycleTop();
  const [search, setSearch] = useState("");
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [selectedEmployee, setSelectedEmployee] = useState<string | null>(null);
  const { data: timeline } = useResourceTimeline(selectedProject);
  const { data: empTimeline } = useEmployeeTimeline(selectedEmployee);
  const { data: searchResults } = useEmployeeSearch(search);

  const panelOpen = !!(selectedProject || selectedEmployee);

  const filteredProjects = useMemo(() => {
    if (!top || !search) return top?.projects ?? [];
    const q = search.toLowerCase();
    return top.projects.filter(p => p.project_id.toLowerCase().includes(q) || p.client.toLowerCase().includes(q));
  }, [top, search]);

  const filteredResources = useMemo(() => {
    if (!top || !search) return top?.resources ?? [];
    const q = search.toLowerCase();
    return top.resources.filter(r => r.employee_id.toLowerCase().includes(q) || (r.job_name ?? "").toLowerCase().includes(q));
  }, [top, search]);

  const handleSelectProject = (pid: string) => { setSelectedProject(pid); setSelectedEmployee(null); };
  const handleSelectEmployee = (eid: string) => { setSelectedEmployee(eid); setSelectedProject(null); };
  const closePanel = () => { setSelectedProject(null); setSelectedEmployee(null); };

  return (
    <div className="flex flex-col h-full">
      <div className="px-8 py-5 bg-white border-b border-gray-100 shrink-0">
        <h1 className="text-xl font-bold" style={{ color: "#19105B" }}>Lifecycle</h1>
        <p className="text-xs text-gray-400 mt-0.5">Click a project or resource to view their timeline</p>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Left: Cards */}
        <div className={`flex-1 overflow-y-auto p-6 space-y-6 transition-all ${panelOpen ? "max-w-[calc(100%-420px)]" : ""}`}>
          {/* Search */}
          <div className="relative max-w-sm">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input value={search} onChange={e => { setSearch(e.target.value); }}
              placeholder="Search project, client, or employee..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-white border border-gray-200 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-200" style={{ color: "#19105B" }} />
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20 gap-2 text-gray-400"><Loader2 className="w-5 h-5 animate-spin" /> Loading...</div>
          ) : (
            <>
              {/* Employee search results */}
              {search.length >= 2 && searchResults && searchResults.length > 0 && (
                <section>
                  <h2 className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-3">Employee Results</h2>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {searchResults.slice(0, 8).map(e => (
                      <button key={e.id} onClick={() => handleSelectEmployee(e.id)}
                        className={`text-left p-3 rounded-xl border transition-all ${selectedEmployee === e.id ? "shadow" : "hover:border-gray-200"}`}
                        style={{ borderColor: selectedEmployee === e.id ? "#19105B" : undefined, background: selectedEmployee === e.id ? "#19105B08" : "#fff" }}>
                        <p className="text-[11px] font-bold truncate" style={{ color: "#19105B" }}>{e.job_name ?? e.id}</p>
                        <p className="text-[10px] text-gray-400 truncate">{e.id} · {e.role ?? "—"}</p>
                      </button>
                    ))}
                  </div>
                </section>
              )}

              {/* Projects */}
              <section>
                <h2 className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-1.5">
                  <Briefcase className="w-3 h-3" /> Projects ({filteredProjects.length})
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                  {filteredProjects.map(p => (
                    <button key={p.project_id} onClick={() => handleSelectProject(p.project_id)}
                      className={`text-left p-3 rounded-xl border transition-all ${selectedProject === p.project_id ? "shadow" : "hover:border-gray-200"}`}
                      style={{ borderColor: selectedProject === p.project_id ? "#19105B" : undefined, background: selectedProject === p.project_id ? "#19105B08" : "#fff" }}>
                      <p className="text-[11px] font-bold truncate" style={{ color: "#19105B" }}>{p.client}</p>
                      <p className="text-[10px] text-gray-400 truncate">{p.project_id}</p>
                      <div className="flex items-center gap-2 mt-1.5 text-[10px] text-gray-400">
                        <span className="flex items-center gap-0.5"><Users className="w-3 h-3" />{p.team_size}</span>
                        {p.coe && <span className="truncate">{p.coe}</span>}
                      </div>
                    </button>
                  ))}
                </div>
              </section>

              {/* Resources */}
              <section>
                <h2 className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-1.5">
                  <Users className="w-3 h-3" /> Resources ({filteredResources.length})
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                  {filteredResources.map(r => (
                    <button key={r.employee_id} onClick={() => handleSelectEmployee(r.employee_id)}
                      className={`text-left p-3 rounded-xl border transition-all ${selectedEmployee === r.employee_id ? "shadow" : "hover:border-gray-200"}`}
                      style={{ borderColor: selectedEmployee === r.employee_id ? "#19105B" : undefined, background: selectedEmployee === r.employee_id ? "#19105B08" : "#fff" }}>
                      <p className="text-[11px] font-bold truncate" style={{ color: "#19105B" }}>{r.job_name ?? r.employee_id}</p>
                      <p className="text-[10px] text-gray-400 truncate">{r.employee_id} · {r.role ?? "—"}</p>
                      <div className="flex items-center gap-2 mt-1.5 text-[10px] text-gray-400">
                        <span>{r.project_count} projects</span>
                        {r.location && <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" />{r.location}</span>}
                      </div>
                    </button>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>

        {/* Right Panel: Timeline */}
        {panelOpen && (
          <div className="w-[420px] shrink-0 border-l border-gray-100 bg-white overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-4 flex items-center justify-between z-10">
              {selectedProject && timeline?.project && (
                <div>
                  <p className="text-sm font-bold" style={{ color: "#19105B" }}>{timeline.project.client}</p>
                  <p className="text-[10px] text-gray-400">{timeline.project.id} · {timeline.project.coe ?? "—"}</p>
                </div>
              )}
              {selectedEmployee && empTimeline?.employee && (
                <div>
                  <p className="text-sm font-bold" style={{ color: "#19105B" }}>{empTimeline.employee.job_name ?? empTimeline.employee.id}</p>
                  <p className="text-[10px] text-gray-400">{empTimeline.employee.id} · {empTimeline.employee.canonical_role ?? "—"} · {empTimeline.employee.location ?? ""}</p>
                </div>
              )}
              <button onClick={closePanel} className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-gray-100">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            {selectedProject && timeline?.project && (
              <>
                <div className="px-5 py-3 border-b border-gray-50 flex items-center gap-4 text-[11px] text-gray-500">
                  <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{timeline.project.start ? new Date(timeline.project.start).toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : "—"} → {timeline.project.end ? new Date(timeline.project.end).toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : "—"}</span>
                  <span className="flex items-center gap-1"><Users className="w-3 h-3" />{timeline.resources.length} resources</span>
                </div>
                {timeline.resources.length > 0 ? (
                  <ProjectGantt project={timeline.project} resources={timeline.resources} />
                ) : (
                  <p className="text-xs text-gray-400 text-center py-12">No allocations</p>
                )}
              </>
            )}

            {selectedEmployee && empTimeline?.employee && (
              <div className="px-5 py-4">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Project Journey (6m back → 6m forward)</p>
                <EmployeeGantt allocations={empTimeline.allocations} />
              </div>
            )}

            {/* Loading state */}
            {((selectedProject && !timeline) || (selectedEmployee && !empTimeline)) && (
              <div className="flex items-center justify-center py-12 text-gray-400"><Loader2 className="w-4 h-4 animate-spin" /></div>
            )}
          </div>
        )}
      </div>
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
      <div className="mb-4">
        <div className="h-2 rounded-full w-full" style={{ background: "#19105B20" }} />
        <div className="flex justify-between text-[9px] text-gray-400 mt-1">
          <span>{project.start ? new Date(project.start).toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : ""}</span>
          <span>{project.end ? new Date(project.end).toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : ""}</span>
        </div>
      </div>
      {resources.map((r, i) => {
        const rStart = r.start_date ? new Date(r.start_date).getTime() : projStart;
        const rEnd = r.end_date ? new Date(r.end_date).getTime() : projEnd;
        const left = Math.max(0, ((rStart - projStart) / span) * 100);
        const width = Math.min(100 - left, Math.max(2, ((rEnd - rStart) / span) * 100));
        return (
          <div key={`${r.employee_id}-${i}`} className="flex items-center gap-2">
            <div className="w-[100px] shrink-0 truncate">
              <p className="text-[10px] font-semibold truncate" style={{ color: "#19105B" }}>{r.job_name ?? r.employee_id}</p>
              <p className="text-[9px] text-gray-400 truncate">{r.canonical_role ?? ""}</p>
            </div>
            <div className="flex-1 h-5 relative bg-gray-50 rounded">
              <div className="absolute top-0.5 bottom-0.5 rounded" style={{ left: `${left}%`, width: `${width}%`, background: STATUS_COLORS[r.status ?? ""] ?? "#94A3B8", opacity: 0.85 }} />
            </div>
            <span className="text-[9px] text-gray-400 w-7 text-right shrink-0">{r.allocation_pct ?? "—"}%</span>
          </div>
        );
      })}
      <div className="flex gap-3 pt-3 border-t border-gray-50 mt-3">
        {Object.entries(STATUS_COLORS).map(([k, v]) => (<span key={k} className="flex items-center gap-1 text-[9px] text-gray-400"><span className="w-2 h-2 rounded-sm" style={{ background: v }} />{k}</span>))}
      </div>
    </div>
  );
}

function EmployeeGantt({ allocations }: {
  allocations: { project_id: string; client: string; coe: string | null; start_date: string | null; end_date: string | null; allocation_pct: number | null; status: string | null; project_status: string | null }[];
}) {
  if (!allocations.length) return <p className="text-xs text-gray-400 text-center py-8">No allocations in this period</p>;
  const now = Date.now();
  const sixBack = now - 6 * 30 * 24 * 60 * 60 * 1000;
  const sixFwd = now + 6 * 30 * 24 * 60 * 60 * 1000;
  const span = sixFwd - sixBack;
  const todayPct = ((now - sixBack) / span) * 100;
  return (
    <div className="space-y-2">
      <div className="relative h-4 mb-2">
        <div className="absolute left-0 right-0 top-1/2 h-px bg-gray-200" />
        <div className="absolute top-0 bottom-0 w-px" style={{ left: `${todayPct}%`, background: "#FF6196" }} />
        <span className="absolute text-[8px] font-bold" style={{ left: `${todayPct}%`, top: -2, transform: "translateX(-50%)", color: "#FF6196" }}>TODAY</span>
        <span className="absolute left-0 bottom-0 text-[8px] text-gray-400">{new Date(sixBack).toLocaleDateString("en-GB", { month: "short", year: "2-digit" })}</span>
        <span className="absolute right-0 bottom-0 text-[8px] text-gray-400">{new Date(sixFwd).toLocaleDateString("en-GB", { month: "short", year: "2-digit" })}</span>
      </div>
      {allocations.map((a, i) => {
        const aStart = a.start_date ? new Date(a.start_date).getTime() : sixBack;
        const aEnd = a.end_date ? new Date(a.end_date).getTime() : sixFwd;
        const left = Math.max(0, ((Math.max(aStart, sixBack) - sixBack) / span) * 100);
        const right = Math.min(100, ((Math.min(aEnd, sixFwd) - sixBack) / span) * 100);
        const width = Math.max(2, right - left);
        const isCurrent = aStart <= now && (aEnd >= now || !a.end_date);
        return (
          <div key={`${a.project_id}-${i}`} className="flex items-center gap-2">
            <div className="w-[90px] shrink-0 truncate">
              <p className="text-[10px] font-semibold truncate" style={{ color: isCurrent ? "#19105B" : "#6b7280" }}>{a.client}</p>
              <p className="text-[9px] text-gray-400 truncate">{a.project_id}</p>
            </div>
            <div className="flex-1 h-6 relative bg-gray-50 rounded">
              <div className="absolute top-0 bottom-0 w-px" style={{ left: `${todayPct}%`, background: "#FF619640" }} />
              <div className="absolute top-1 bottom-1 rounded" style={{ left: `${left}%`, width: `${width}%`, background: STATUS_COLORS[a.status ?? ""] ?? "#94A3B8", opacity: isCurrent ? 1 : 0.5 }} />
            </div>
            <span className="text-[9px] text-gray-400 w-7 text-right shrink-0">{a.allocation_pct ?? "—"}%</span>
          </div>
        );
      })}
      <div className="flex gap-3 pt-3 border-t border-gray-50 mt-3">
        {Object.entries(STATUS_COLORS).map(([k, v]) => (<span key={k} className="flex items-center gap-1 text-[9px] text-gray-400"><span className="w-2 h-2 rounded-sm" style={{ background: v }} />{k}</span>))}
        <span className="flex items-center gap-1 text-[9px] ml-auto" style={{ color: "#FF6196" }}><span className="w-px h-3" style={{ background: "#FF6196" }} /> Today</span>
      </div>
    </div>
  );
}
