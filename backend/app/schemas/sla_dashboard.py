from pydantic import BaseModel


class SLATargetSummary(BaseModel):
    total: int = 0
    on_track: int = 0
    at_risk: int = 0
    breached: int = 0
    met: int = 0


class SLAPriorityBreakdown(BaseModel):
    response: SLATargetSummary
    resolution: SLATargetSummary


class SLADashboardResponse(BaseModel):
    organisation_id: str
    total_tickets: int

    response_compliance_percent: float
    resolution_compliance_percent: float

    response: SLATargetSummary
    resolution: SLATargetSummary

    priority_breakdown: dict[str, SLAPriorityBreakdown]
