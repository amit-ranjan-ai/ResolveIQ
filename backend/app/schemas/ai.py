from uuid import UUID

from pydantic import BaseModel, Field


class TicketClassificationRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)


class CategorySuggestion(BaseModel):
    category_id: UUID | None
    category_name: str | None
    confidence: int = Field(ge=0, le=100)
    confidence_level: str
    matched_keywords: list[str] = Field(default_factory=list)
    explanation: str


class FieldSuggestion(BaseModel):
    value: str | None
    confidence: int = Field(ge=0, le=100)
    confidence_level: str
    matched_keywords: list[str]
    explanation: str


class TeamSuggestion(BaseModel):
    team_id: UUID | None
    team_name: str | None
    confidence: int = Field(ge=0, le=100)
    confidence_level: str
    explanation: str


class TicketClassificationResponse(BaseModel):
    category: CategorySuggestion
    impact: FieldSuggestion
    urgency: FieldSuggestion
    priority: str | None
    team: TeamSuggestion
    requires_human_review: bool
    overall_confidence: int = Field(ge=0, le=100)
    fields_requiring_review: list[str] = Field(default_factory=list)
    confidence_type: str = "heuristic"


class TicketReplySuggestionResponse(BaseModel):
    ticket_id: UUID
    ticket_number: str
    suggested_reply: str
    model: str
    context_comment_count: int = Field(ge=0)
    requires_human_review: bool = True
