
import { Bell, Search, Sparkles, Menu } from "lucide-react"
import { useLocation } from "react-router-dom"

interface AppHeaderProps {
  onMenuClick?: () => void
}

const pageInfo: Record<string, { title: string; description: string }> = {
  "/": {
    title: "Dashboard",
    description: "Welcome back! Here's your IT operations overview.",
  },
  "/tickets": {
    title: "Tickets",
    description: "Manage and track IT support requests.",
  },
  "/knowledge-base": {
    title: "Knowledge Base",
    description: "Explore IT guides and troubleshooting resources.",
  },
  "/users": {
    title: "Users",
    description: "Manage employees and IT support team members.",
  },
  "/reports": {
    title: "Reports",
    description: "Monitor support performance and IT operations.",
  },
  "/settings": {
    title: "Settings",
    description: "Manage your application and organisation preferences.",
  },
}

export function AppHeader({ onMenuClick }: AppHeaderProps) {
  const location = useLocation()
  const currentPage = pageInfo[location.pathname] ?? pageInfo["/"]

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b bg-background/95 px-4 backdrop-blur sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          aria-label="Open navigation menu"
          onClick={onMenuClick}
          className="flex size-9 shrink-0 items-center justify-center rounded-lg border transition-colors hover:bg-accent md:hidden"
        >
          <Menu className="size-5" />
        </button>

        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold tracking-tight">
            {currentPage.title}
          </h2>
          <p className="hidden text-xs text-muted-foreground sm:block">
            {currentPage.description}
          </p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <div className="hidden items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2 lg:flex">
          <Search className="size-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            Search anything...
          </span>
          <kbd className="rounded border bg-background px-1.5 py-0.5 text-xs text-muted-foreground">
            /
          </kbd>
        </div>

        <button
          type="button"
          aria-label="AI assistant"
          className="flex size-9 items-center justify-center rounded-lg border transition-colors hover:bg-accent"
        >
          <Sparkles className="size-4" />
        </button>

        <button
          type="button"
          aria-label="Notifications"
          className="relative flex size-9 items-center justify-center rounded-lg border transition-colors hover:bg-accent"
        >
          <Bell className="size-4" />
          <span className="absolute right-2 top-2 size-2 rounded-full bg-destructive" />
        </button>

        <div className="flex size-9 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
          A
        </div>
      </div>
    </header>
  )
}


