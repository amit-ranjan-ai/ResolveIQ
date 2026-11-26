import { api } from "./api";

export interface TicketActivity {
  id: string;
  organisation_id: string;
  ticket_id: string;
  actor_membership_id: string;
  activity_type: string;
  description: string;
  old_value: string | null;
  new_value: string | null;
  extra_data: Record<string, unknown> | null;
  created_at: string;
}

export async function getTicketActivities(
  ticketId: string,
): Promise<TicketActivity[]> {
  const response = await api.get<TicketActivity[]>(
    `/tickets/${ticketId}/activities`,
  );

  return response.data;
}
