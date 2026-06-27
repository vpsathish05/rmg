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
    <aside
      className="w-56 shrink-0 flex flex-col bg-white"
      style={{ borderRight: "1px solid #E8E8E8" }}
    >
      {/* Brand */}
      <div className="px-5 pt-6 pb-5" style={{ borderBottom: "1px solid #F2F2F2" }}>
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 font-black text-xs text-white"
            style={{ background: "#19105B" }}
          >
            JG
          </div>
          <div>
            <p className="text-sm font-bold leading-none" style={{ color: "#19105B" }}>RMG Engine</p>
            <p className="text-[10px] mt-0.5 font-medium" style={{ color: "#94A3B8" }}>JMan Group</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all duration-150"
              style={active ? { background: "#3411A3", color: "#fff" } : { color: "#64748B" }}
              onMouseEnter={(e) => {
                if (!active) {
                  (e.currentTarget as HTMLElement).style.background = "#F2F2F2";
                  (e.currentTarget as HTMLElement).style.color = "#19105B";
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                  (e.currentTarget as HTMLElement).style.color = "#64748B";
                }
              }}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User profile with sign out */}
      <div className="px-3 pb-4" style={{ borderTop: "1px solid #F2F2F2", paddingTop: "12px" }}>
        <div
          className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg"
          style={{ background: "#F5F5F5" }}
        >
          {/* Avatar */}
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold text-white"
            style={{ background: "#3411A3" }}
          >
            {initials}
          </div>

          {/* Name + role */}
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold truncate leading-none" style={{ color: "#19105B" }}>
              {displayName}
            </p>
            <p className="text-[10px] mt-0.5 truncate" style={{ color: "#94A3B8" }}>RMG Lead</p>
          </div>

          {/* Sign out icon — inside the card */}
          <form action={logout}>
            <button
              type="submit"
              title="Sign out"
              className="w-6 h-6 rounded-md flex items-center justify-center transition-all shrink-0"
              style={{ color: "#94A3B8" }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = "#FFF0F4";
                (e.currentTarget as HTMLElement).style.color = "#A6265E";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = "transparent";
                (e.currentTarget as HTMLElement).style.color = "#94A3B8";
              }}
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>
    </aside>
  );
}
