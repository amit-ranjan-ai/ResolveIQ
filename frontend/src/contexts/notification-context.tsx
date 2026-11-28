import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/contexts/auth-context";
import { useOrganisation } from "@/contexts/organisation-context";

import {
  connectNotificationWebSocket,
  type LiveNotification,
} from "@/services/notification-websocket";

import {
  getNotifications,
  getUnreadNotificationCount,
  markNotificationAsRead,
  markAllNotificationsAsRead,
} from "@/services/notifications";

interface NotificationContextType {
  notifications: LiveNotification[];
  unreadCount: number;
  isConnected: boolean;
  isLoading: boolean;
  refreshNotifications: () => Promise<void>;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(
  undefined,
);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { user, isLoading: isAuthLoading } = useAuth();
  const { selectedOrganisationId } = useOrganisation();

  const [notifications, setNotifications] = useState<LiveNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const refreshNotifications = useCallback(async () => {
    if (!selectedOrganisationId) return;

    setIsLoading(true);

    try {
      const [notificationData, unreadCountData] = await Promise.all([
        getNotifications(selectedOrganisationId),
        getUnreadNotificationCount(selectedOrganisationId),
      ]);

      setNotifications(notificationData);
      setUnreadCount(unreadCountData);
    } catch (error) {
      console.error("Failed to load notifications:", error);
    } finally {
      setIsLoading(false);
    }
  }, [selectedOrganisationId]);

  const markAsRead = useCallback(
    async (notificationId: string) => {
      if (!selectedOrganisationId) return;

      try {
        const updatedNotification = await markNotificationAsRead(
          selectedOrganisationId,
          notificationId,
        );

        setNotifications((current) =>
          current.map((notification) =>
            notification.id === notificationId
              ? updatedNotification
              : notification,
          ),
        );

        if (
          !notifications.find((item) => item.id === notificationId)?.is_read
        ) {
          setUnreadCount((count) => Math.max(0, count - 1));
        }
      } catch (error) {
        console.error("Failed to mark notification as read:", error);
        throw error;
      }
    },
    [selectedOrganisationId, notifications],
  );

  const markAllAsRead = useCallback(async () => {
    if (!selectedOrganisationId) return;

    try {
      await markAllNotificationsAsRead(selectedOrganisationId);

      const readAt = new Date().toISOString();

      setNotifications((current) =>
        current.map((notification) => ({
          ...notification,
          is_read: true,
          read_at: notification.read_at ?? readAt,
        })),
      );

      setUnreadCount(0);
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
      throw error;
    }
  }, [selectedOrganisationId]);

  const addNotification = useCallback((notification: LiveNotification) => {
    setNotifications((current) => {
      if (current.some((item) => item.id === notification.id)) {
        return current;
      }

      return [notification, ...current].slice(0, 100);
    });

    if (!notification.is_read) {
      setUnreadCount((count) => count + 1);
    }
  }, []);

  useEffect(() => {
    if (isAuthLoading) return;

    if (!user || !selectedOrganisationId) {
      setNotifications([]);
      setUnreadCount(0);
      setIsConnected(false);
      setIsLoading(false);
      return;
    }

    void refreshNotifications();

    const disconnect = connectNotificationWebSocket({
      organisationId: selectedOrganisationId,
      onNotification: addNotification,
      onConnected: () => setIsConnected(true),
      onDisconnected: () => setIsConnected(false),
    });

    return () => {
      disconnect();
      setIsConnected(false);
    };
  }, [
    user?.id,
    isAuthLoading,
    selectedOrganisationId,
    refreshNotifications,
    addNotification,
  ]);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        isConnected,
        isLoading,
        refreshNotifications,
        markAsRead,
        markAllAsRead,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);

  if (!context) {
    throw new Error(
      "useNotifications must be used inside NotificationProvider",
    );
  }

  return context;
}
