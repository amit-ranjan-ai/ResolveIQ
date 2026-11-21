

import { useState } from "react"
import type { ReactNode } from "react"
import { Link, useLocation } from "react-router-dom"
import { ChevronRight, Home } from "lucide-react"

import { AppHeader } from "@/components/layout/app-header"
import { AppSidebar } from "@/components/layout/app-sidebar"

interface AppLayoutProps {
  children: ReactNode
}

const breadcrumbNames: Record<string, string> = {
  tickets: "Tickets",
  "knowledge-base": "Knowledge Base",
  users: "Users",
  reports: "Reports",
  settings: "Settings",
}

export function AppLayout({ children }: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const currentSegment = location.pathname.split("/").filter(Boolean)
  const currentPage = currentSegment[currentSegment.length - 1]

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <AppSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader onMenuClick={() => setSidebarOpen(true)} />

        <main className="min-w-0 flex-1 overflow-y-auto p-4 sm:p-6">
          <nav
            aria-label="Breadcrumb"
            className="mb-5 flex items-center gap-2 text-sm"
          >
            <Link
              to="/"
              className="flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-foreground"
            >
              <Home className="size-4" />
              <span>Home</span>
            </Link>

            {currentPage && (
              <>
                <ChevronRight className="size-4 text-muted-foreground" />

                <span className="font-medium text-foreground">
                  {breadcrumbNames[currentPage] ?? currentPage}
                </span>
              </>
            )}
          </nav>

          {children}
        </main>
      </div>
    </div>
  )
}


