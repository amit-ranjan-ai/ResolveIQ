import { api } from "./api";

export interface OrganisationTicket {
  id: string;
  organisation_id: string;
  ticket_number: string;
  requester_membership_id: string;
  category_id: string | null;
  assigned_team_id: string | null;
  assigned_agent_membership_id: string | null;
  subject: string;
  description: string;
  status: string;
  priority: "P1" | "P2" | "P3" | "P4";
  impact: string;
  urgency: string;
  source: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface CreateTicketPayload {
  requester_membership_id: string;
  category_id: string | null;
  subject: string;
  description: string;
  impact: "LOW" | "MEDIUM" | "HIGH";
  urgency: "LOW" | "MEDIUM" | "HIGH";
  source: "WEB";
}

export async function getOrganisationTickets(
  organisationId: string,
): Promise<OrganisationTicket[]> {
  const response = await api.get<OrganisationTicket[]>(
    `/organisations/${organisationId}/tickets`,
  );

  return response.data;
}

export async function createOrganisationTicket(
  organisationId: string,
  payload: CreateTicketPayload,
): Promise<OrganisationTicket> {
  const response = await api.post<OrganisationTicket>(
    `/organisations/${organisationId}/tickets`,
    payload,
  );

  return response.data;
}

export async function updateTicket(
  ticketId: string,
  payload: { status: string },
): Promise<OrganisationTicket> {
  const response = await api.patch<OrganisationTicket>(
    `/tickets/${ticketId}`,
    payload,
  );

  return response.data;
}
