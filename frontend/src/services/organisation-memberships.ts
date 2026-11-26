import { api } from "./api";

export interface OrganisationMembership {
  id: string;
  organisation_id: string;
  user_id: string;
  role: string;
  is_active: boolean;
}

export async function getMyOrganisationMembership(
  organisationId: string,
): Promise<OrganisationMembership> {
  const response = await api.get<OrganisationMembership>(
    `/organisations/${organisationId}/my-membership`,
  );

  return response.data;
}
