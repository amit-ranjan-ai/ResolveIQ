import { useState } from "react";
import {
  Bell,
  Search,
  Sparkles,
  Menu,
  Command,
  CheckCheck,
  Circle,
  LoaderCircle,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { useLocation } from "react-router-dom";

import { useNotifications } from "@/contexts/notification-context";

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

  const {
    notifications,
    unreadCount,
    isConnected,
    isLoading,
    markAsRead,
    markAllAsRead,
    refreshNotifications,
  } = useNotifications();

  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const currentPage = pageInfo[location.pathname] ?? pageInfo["/"];

  async function handleMarkAllAsRead() {
    setActionLoading(true);

    try {
      await markAllAsRead();
    } catch (error) {
      console.error("Unable to mark all notifications as read:", error);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleNotificationClick(
    notificationId: string,
    isRead: boolean,
  ) {
    if (isRead) return;

    try {
      await markAsRead(notificationId);
    } catch (error) {
      console.error("Unable to mark notification as read:", error);
    }
  }

  function formatNotificationDate(date: string) {
    const notificationDate = new Date(date);

    if (Number.isNaN(notificationDate.getTime())) {
      return "Recently";
    }

    return new Intl.DateTimeFormat("en-IN", {
      day: "numeric",
      month: "short",
      hour: "numeric",
      minute: "2-digit",
    }).format(notificationDate);
  }

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
        <div className="relative">
          <button
            type="button"
            aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}
            aria-expanded={notificationsOpen}
            aria-haspopup="dialog"
            title="Notifications"
            onClick={() => {
              const opening = !notificationsOpen;
              setNotificationsOpen(opening);

              if (opening) {
                void refreshNotifications();
              }
            }}
            className={`relative flex size-10 items-center justify-center rounded-xl border bg-white transition-all hover:bg-slate-50 hover:text-slate-900 ${
              notificationsOpen
                ? "border-blue-200 text-blue-600"
                : "border-slate-200 text-slate-500"
            }`}
          >
            <Bell className="size-[17px]" />

            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-[19px] min-w-[19px] items-center justify-center rounded-full border-2 border-white bg-blue-600 px-1 text-[9px] font-bold text-white">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>

          {notificationsOpen && (
            <div
              role="dialog"
              aria-label="Notifications"
              className="absolute right-0 top-12 z-50 w-[min(380px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/10"
            >
              {/* Dropdown header */}
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Notifications
                  </h3>

                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {unreadCount} unread notifications
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {unreadCount > 0 && (
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => void handleMarkAllAsRead()}
                      className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-[11px] font-semibold text-blue-600 transition-colors hover:bg-blue-50 disabled:opacity-50"
                    >
                      <CheckCheck className="size-3.5" />
                      Mark all read
                    </button>
                  )}

                  <button
                    type="button"
                    aria-label="Close notifications"
                    onClick={() => setNotificationsOpen(false)}
                    className="flex size-7 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                  >
                    <X className="size-4" />
                  </button>
                </div>
              </div>

              {/* Connection status */}
              <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-4 py-2">
                <div className="flex items-center gap-1.5">
                  {isConnected ? (
                    <Wifi className="size-3 text-emerald-600" />
                  ) : (
                    <WifiOff className="size-3 text-slate-400" />
                  )}

                  <span className="text-[10px] font-medium text-slate-500">
                    {isConnected
                      ? "Live updates connected"
                      : "Connecting to live updates..."}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => void refreshNotifications()}
                  aria-label="Refresh notifications"
                  className="text-[10px] font-semibold text-blue-600 hover:text-blue-700"
                >
                  Refresh
                </button>
              </div>

              {/* Notification list */}
              <div className="max-h-[390px] overflow-y-auto">
                {isLoading ? (
                  <div className="flex flex-col items-center justify-center gap-2 px-4 py-12">
                    <LoaderCircle className="size-5 animate-spin text-blue-500" />
                    <p className="text-xs text-slate-500">
                      Loading notifications...
                    </p>
                  </div>
                ) : notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center px-4 py-12 text-center">
                    <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-slate-100">
                      <Bell className="size-5 text-slate-400" />
                    </div>

                    <p className="text-sm font-semibold text-slate-700">
                      You're all caught up
                    </p>

                    <p className="mt-1 text-xs text-slate-400">
                      New notifications will appear here.
                    </p>
                  </div>
                ) : (
                  notifications.map((notification) => (
                    <button
                      key={notification.id}
                      type="button"
                      onClick={() =>
                        void handleNotificationClick(
                          notification.id,
                          notification.is_read,
                        )
                      }
                      className={`flex w-full gap-3 border-b border-slate-100 px-4 py-3 text-left transition-colors hover:bg-slate-50 ${
                        notification.is_read ? "bg-white" : "bg-blue-50/40"
                      }`}
                    >
                      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                        <Bell className="size-4" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-xs font-semibold text-slate-800">
                            {notification.title}
                          </p>

                          {!notification.is_read && (
                            <Circle className="mt-1 size-2 shrink-0 fill-blue-600 text-blue-600" />
                          )}
                        </div>

                        <p className="mt-1 text-[11px] leading-relaxed text-slate-600">
                          {notification.message}
                        </p>

                        <p className="mt-1.5 text-[10px] text-slate-400">
                          {formatNotificationDate(notification.created_at)}
                        </p>
                      </div>
                    </button>
                  ))
                )}
              </div>

              {/* Dropdown footer */}
              {notifications.length > 0 && (
                <div className="border-t border-slate-100 bg-slate-50/70 px-4 py-2.5">
                  <p className="text-center text-[10px] text-slate-500">
                    Showing the latest {notifications.length} notifications
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

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
