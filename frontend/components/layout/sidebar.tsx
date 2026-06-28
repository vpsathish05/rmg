"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, TrendingUp, Cpu, LogOut } from "lucide-react";
import { logout } from "@/lib/actions";

const NAV = [
  { href: "/rmg-engine", label: "RMG Engine",  icon: Cpu },
  { href: "/forecast",   label: "Forecast",    icon: TrendingUp },
  { href: "/",           label: "Dashboard",   icon: LayoutDashboard },
];

export default function Sidebar({ userName = "RMG User" }: { userName?: string }) {
  const path = usePathname();

  const displayName = userName
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .split(/[\s._-]+/)
    .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

  const initials = displayName
    .split(" ")
    .map((w: string) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) || "RG";

  return (
    <aside className="w-[220px] shrink-0 flex flex-col bg-white border-r border-gray-100">
      {/* Brand */}
      <div className="px-5 pt-6 pb-5 border-b border-gray-50">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 font-black text-sm text-white bg-gradient-to-br from-violet-700 to-violet-900">
            J
          </div>
          <div>
            <p className="text-sm font-bold text-gray-900 leading-none">RMG Engine</p>
            <p className="text-[10px] mt-0.5 font-medium text-gray-400">JMan Group</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link key={href} href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150"
              style={active
                ? { background: "#7c3aed", color: "#fff", boxShadow: "0 2px 8px rgba(124,58,237,0.25)" }
                : { color: "#6b7280" }
              }
              onMouseEnter={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = "#f3f4f6"; (e.currentTarget as HTMLElement).style.color = "#111827"; }}}
              onMouseLeave={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = "#6b7280"; }}}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="px-3 pb-4 pt-3 border-t border-gray-50">
        <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-gray-50">
          <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold text-white bg-violet-600">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold truncate text-gray-900">{displayName}</p>
            <p className="text-[10px] truncate text-gray-400">RMG Lead</p>
          </div>
          <form action={logout}>
            <button type="submit" title="Sign out"
              className="w-7 h-7 rounded-lg flex items-center justify-center text-gray-400 hover:bg-red-50 hover:text-red-500 transition-all shrink-0">
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>
    </aside>
  );
}
