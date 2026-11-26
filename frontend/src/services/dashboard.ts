import { api } from "./api";

export interface Organisation {
  id: string;
  name: string;
}

export interface SLAStatusSummary {
  total: number;
  on_track: number;
  at_risk: number;
  breached: number;
  met: number;
}

export interface SLADashboard {
  organisation_id: string;
  total_tickets: number;
  response_compliance_percent: number;
  resolution_compliance_percent: number;
  response: SLAStatusSummary;
  resolution: SLAStatusSummary;
}

export async function getOrganisations(): Promise<Organisation[]> {
  const response = await api.get<Organisation[]>("/organisations/");
  return response.data;
}

export async function getSLADashboard(
  organisationId: string,
): Promise<SLADashboard> {
  const response = await api.get<SLADashboard>(
    `/organisations/${organisationId}/sla-dashboard`,
  );

  return response.data;
}
