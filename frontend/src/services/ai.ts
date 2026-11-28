import { api } from "./api";

export interface TicketClassificationRequest {
  subject: string;
  description: string;
}

export interface CategorySuggestion {
  category_id: string | null;
  category_name: string | null;
  confidence: number;
  confidence_level: string;
  matched_keywords: string[];
  explanation: string;
}

export interface FieldSuggestion {
  value: string | null;
  confidence: number;
  confidence_level: string;
  matched_keywords: string[];
  explanation: string;
}

export interface TeamSuggestion {
  team_id: string | null;
  team_name: string | null;
  confidence: number;
  confidence_level: string;
  explanation: string;
}

export interface TicketClassificationResponse {
  category: CategorySuggestion;
  impact: FieldSuggestion;
  urgency: FieldSuggestion;
  priority: string | null;
  team: TeamSuggestion;
  requires_human_review: boolean;
  overall_confidence: number;
  fields_requiring_review: string[];
  confidence_type: string;
}

export interface TicketReplySuggestionResponse {
  ticket_id: string;
  ticket_number: string;
  suggested_reply: string;
  model: string;
  context_comment_count: number;
  requires_human_review: boolean;
}

export async function classifyTicket(
  organisationId: string,
  payload: TicketClassificationRequest,
): Promise<TicketClassificationResponse> {
  const response = await api.post<TicketClassificationResponse>(
    `/organisations/${organisationId}/ai/classify-ticket`,
    payload,
  );

  return response.data;
}

export async function suggestTicketReply(
  ticketId: string,
): Promise<TicketReplySuggestionResponse> {
  const response = await api.post<TicketReplySuggestionResponse>(
    `/tickets/${ticketId}/ai/suggest-reply`,
    {},
    { timeout: 60000 },
  );

  return response.data;
}
