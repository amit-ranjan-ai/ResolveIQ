import { api } from "@/services/api";
import type { LiveNotification } from "@/services/notification-websocket";

export interface UnreadNotificationCountResponse {
  unread_count: number;
}

export interface MarkAllNotificationsReadResponse {
  updated_count: number;
}

export async function getNotifications(
  organisationId: string,
  unreadOnly = false,
  limit = 50,
): Promise<LiveNotification[]> {
  const response = await api.get<LiveNotification[]>(
    `/organisations/${organisationId}/notifications`,
    {
      params: {
        unread_only: unreadOnly,
        limit,
      },
    },
  );

  return response.data;
}

export async function getUnreadNotificationCount(
  organisationId: string,
): Promise<number> {
  const response = await api.get<UnreadNotificationCountResponse>(
    `/organisations/${organisationId}/notifications/unread-count`,
  );

  return response.data.unread_count;
}

export async function markNotificationAsRead(
  organisationId: string,
  notificationId: string,
): Promise<LiveNotification> {
  const response = await api.patch<LiveNotification>(
    `/organisations/${organisationId}/notifications/${notificationId}/read`,
  );

  return response.data;
}

export async function markAllNotificationsAsRead(
  organisationId: string,
): Promise<number> {
  const response = await api.patch<MarkAllNotificationsReadResponse>(
    `/organisations/${organisationId}/notifications/read-all`,
  );

  return response.data.updated_count;
}
