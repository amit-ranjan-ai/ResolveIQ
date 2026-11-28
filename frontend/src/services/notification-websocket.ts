import { getAccessToken } from "@/services/auth";

export interface LiveNotification {
  id: string;
  organisation_id: string;
  recipient_membership_id: string;
  ticket_id: string | null;
  notification_type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

interface WebSocketMessage {
  type: "CONNECTED" | "NEW_NOTIFICATION";
  notification?: LiveNotification;
}

interface NotificationWebSocketOptions {
  organisationId: string;
  onNotification: (notification: LiveNotification) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

export function connectNotificationWebSocket({
  organisationId,
  onNotification,
  onConnected,
  onDisconnected,
}: NotificationWebSocketOptions): () => void {
  let socket: WebSocket | null = null;
  let reconnectTimer: number | undefined;
  let stopped = false;
  let reconnectDelay = 2000;

  function connect() {
    if (stopped) return;

    const token = getAccessToken();

    if (!token) {
      return;
    }

    const apiUrl = new URL(import.meta.env.VITE_API_BASE_URL);

    apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";

    apiUrl.pathname =
      `${apiUrl.pathname.replace(/\/$/, "")}` +
      `/organisations/${encodeURIComponent(organisationId)}` +
      "/notifications/ws";

    apiUrl.search = "";

    socket = new WebSocket(apiUrl.toString());

    socket.onopen = () => {
      socket?.send(JSON.stringify({ token }));
    };

    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage;

        if (data.type === "CONNECTED") {
          reconnectDelay = 2000;
          onConnected?.();
        }

        if (data.type === "NEW_NOTIFICATION" && data.notification) {
          onNotification(data.notification);
        }
      } catch {
        console.error("Invalid notification WebSocket message.");
      }
    };

    socket.onclose = () => {
      onDisconnected?.();

      if (!stopped) {
        reconnectTimer = window.setTimeout(() => {
          connect();
        }, reconnectDelay);

        reconnectDelay = Math.min(reconnectDelay * 2, 30000);
      }
    };

    socket.onerror = () => {
      socket?.close();
    };
  }

  connect();

  return () => {
    stopped = true;

    if (reconnectTimer !== undefined) {
      window.clearTimeout(reconnectTimer);
    }

    socket?.close();
    socket = null;
  };
}
