import {
  LayoutDashboard,
  Ticket,
  BookOpen,
  Users,
  BarChart3,
  Settings,
  Headset,
  X,
  ChevronRight,
  Sparkles,
  LogOut,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/contexts/auth-context";

const navigation = [
  {
    title: "Workspace",
    items: [
      { label: "Dashboard", path: "/", icon: LayoutDashboard },
      { label: "Tickets", path: "/tickets", icon: Ticket },
      { label: "Knowledge Base", path: "/knowledge-base", icon: BookOpen },
    ],
  },
  {
    title: "Administration",
    items: [
      { label: "Users & Teams", path: "/users", icon: Users },
      { label: "Reports & Analytics", path: "/reports", icon: BarChart3 },
      { label: "Settings", path: "/settings", icon: Settings },
    ],
  },
];

interface AppSidebarProps {
  open?: boolean;
  onClose?: () => void;
}

export function AppSidebar({ open = true, onClose }: AppSidebarProps) {
  const { user, logout } = useAuth();

  const initials =
    user?.full_name
      ?.trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || "U";

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close navigation overlay"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-sm md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-screen w-64 shrink-0 flex-col border-r border-slate-200/80 bg-white text-slate-800 shadow-xl shadow-slate-200/30 transition-transform duration-300 md:sticky md:top-0 md:z-20 md:translate-x-0 md:shadow-none ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-[76px] shrink-0 items-center justify-between border-b border-slate-100 px-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-600/20">
              <Headset className="size-5" />
            </div>

            <div>
              <h1 className="text-[17px] font-bold tracking-tight text-slate-900">
                ResolveIQ
              </h1>
              <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-400">
                Operations Intelligence
              </p>
            </div>
          </div>

          <button
            type="button"
            aria-label="Close sidebar"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 md:hidden"
          >
            <X className="size-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-8 overflow-y-auto px-3 py-7">
          {navigation.map((section) => (
            <div key={section.title}>
              <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">
                {section.title}
              </p>

              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;

                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === "/"}
                      onClick={onClose}
                      className={({ isActive }) =>
                        `group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-[13px] font-medium transition-all duration-200 ${
                          isActive
                            ? "bg-blue-50 text-blue-700 shadow-sm shadow-blue-100/70"
                            : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <Icon
                            className={`size-[18px] shrink-0 transition-colors ${
                              isActive
                                ? "text-blue-600"
                                : "text-slate-400 group-hover:text-slate-700"
                            }`}
                          />

                          <span className="flex-1">{item.label}</span>

                          {isActive && (
                            <ChevronRight className="size-4 text-blue-500" />
                          )}
                        </>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="px-4 pb-4">
          <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 to-indigo-50 p-4">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="size-4 text-blue-600" />
              <span className="text-xs font-bold text-blue-900">
                ResolveIQ Intelligence
              </span>
            </div>

            <p className="text-[11px] leading-relaxed text-slate-600">
              Your workspace for smarter IT support and operations.
            </p>
          </div>
        </div>

        <div className="shrink-0 border-t border-slate-100 p-4">
          <div className="flex items-center gap-3 rounded-xl p-2">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-sm font-bold text-white shadow-sm">
              {initials}
            </div>

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-800">
                {user?.full_name || "Loading user..."}
              </p>
              <p className="truncate text-xs text-slate-400">
                {user?.email || ""}
              </p>
            </div>

            <button
              type="button"
              onClick={logout}
              title="Sign out"
              aria-label="Sign out"
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
