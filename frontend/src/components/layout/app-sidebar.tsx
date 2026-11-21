
import {
  LayoutDashboard,
  Ticket,
  BookOpen,
  Users,
  BarChart3,
  Settings,
  Headset,
  X,
} from "lucide-react"
import { NavLink } from "react-router-dom"

const navigation = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", path: "/", icon: LayoutDashboard },
      { label: "Tickets", path: "/tickets", icon: Ticket },
      { label: "Knowledge Base", path: "/knowledge-base", icon: BookOpen },
    ],
  },
  {
    title: "Management",
    items: [
      { label: "Users", path: "/users", icon: Users },
      { label: "Reports", path: "/reports", icon: BarChart3 },
      { label: "Settings", path: "/settings", icon: Settings },
    ],
  },
]

interface AppSidebarProps {
  open?: boolean
  onClose?: () => void
}

export function AppSidebar({ open = true, onClose }: AppSidebarProps) {
  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close navigation overlay"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-screen w-64 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground transition-transform duration-200 md:sticky md:top-0 md:z-20 md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 shrink-0 items-center justify-between border-b px-5">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Headset className="size-5" />
            </div>

            <div>
              <h1 className="text-lg font-bold tracking-tight">ResolveIQ</h1>
              <p className="text-xs text-muted-foreground">
                IT Operations Intelligence
              </p>
            </div>
          </div>

          <button
            type="button"
            aria-label="Close sidebar"
            onClick={onClose}
            className="rounded-lg p-2 hover:bg-accent md:hidden"
          >
            <X className="size-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-7 overflow-y-auto px-3 py-6">
          {navigation.map((section) => (
            <div key={section.title}>
              <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {section.title}
              </p>

              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon

                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === "/"}
                      onClick={onClose}
                      className={({ isActive }) =>
                        `flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        }`
                      }
                    >
                      <Icon className="size-4" />
                      {item.label}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="shrink-0 border-t p-4">
          <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-3">
            <div className="flex size-9 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
              A
            </div>

            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">Admin User</p>
              <p className="truncate text-xs text-muted-foreground">
                IT Administrator
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}


