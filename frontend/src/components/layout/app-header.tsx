import { Bell, Search, Sparkles, Menu, Command } from "lucide-react";
import { useLocation } from "react-router-dom";

interface AppHeaderProps {
  onMenuClick?: () => void;
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
    title: "Reports & Analytics",
    description: "Monitor support performance and IT operations.",
  },
  "/settings": {
    title: "Settings",
    description: "Manage your application and organisation preferences.",
  },
};

export function AppHeader({ onMenuClick }: AppHeaderProps) {
  const location = useLocation();
  const currentPage = pageInfo[location.pathname] ?? pageInfo["/"];

  return (
    <header className="sticky top-0 z-30 flex h-[76px] shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
      {/* Page information */}
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          aria-label="Open navigation menu"
          onClick={onMenuClick}
          className="flex size-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition-colors hover:bg-slate-50 md:hidden"
        >
          <Menu className="size-[18px]" />
        </button>

        <div className="min-w-0">
          <h2 className="truncate text-lg font-bold tracking-tight text-slate-900 sm:text-xl">
            {currentPage.title}
          </h2>

          <p className="mt-0.5 hidden text-xs text-slate-500 sm:block">
            {currentPage.description}
          </p>
        </div>
      </div>

      {/* Header actions */}
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        {/* Search */}
        <button
          type="button"
          aria-label="Search"
          className="hidden h-10 w-56 items-center gap-2.5 rounded-xl border border-slate-200 bg-slate-50/70 px-3 text-left transition-all hover:border-blue-200 hover:bg-blue-50/40 lg:flex xl:w-64"
        >
          <Search className="size-4 text-slate-400" />

          <span className="flex-1 text-xs text-slate-400">
            Search anything...
          </span>

          <kbd className="flex items-center gap-0.5 rounded-md border border-slate-200 bg-white px-1.5 py-1 text-[10px] font-medium text-slate-400">
            <Command className="size-2.5" />K
          </kbd>
        </button>

        {/* AI assistant */}
        <button
          type="button"
          aria-label="AI assistant"
          title="AI assistant"
          className="flex size-10 items-center justify-center rounded-xl border border-blue-100 bg-blue-50/70 text-blue-600 transition-all hover:border-blue-200 hover:bg-blue-100"
        >
          <Sparkles className="size-[17px]" />
        </button>

        {/* Notifications */}
        <button
          type="button"
          aria-label="Notifications"
          title="Notifications"
          className="relative flex size-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition-all hover:bg-slate-50 hover:text-slate-900"
        >
          <Bell className="size-[17px]" />

          <span className="absolute right-[9px] top-[8px] size-2 rounded-full border-2 border-white bg-blue-600" />
        </button>

        {/* User avatar */}
        <div
          title="Admin User"
          className="flex size-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-sm font-bold text-white shadow-sm ring-2 ring-blue-50"
        >
          A
        </div>
      </div>
    </header>
  );
}
