from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.services.ai.confidence import get_confidence_level
from app.services.ai.rule_based_classifier import (
    CATEGORY_KEYWORDS,
    keyword_matches,
    suggest_category,
    suggest_impact,
    suggest_urgency,
)
from app.services.ai.text_preprocessing import normalize_ticket_text
from app.services.ticket_priority import calculate_ticket_priority


def suggest_team(
    db: Session,
    organisation_id,
    category_name: str | None = None,
) -> dict:
    """
    Find eligible teams and optionally recommend one using category expertise.

    Only teams belonging to the current organisation are considered.
    No team assignment is performed.
    """

    eligible_teams = db.scalars(
        select(Team)
        .join(
            TeamMembership,
            TeamMembership.team_id == Team.id,
        )
        .join(
            OrganisationMembership,
            OrganisationMembership.id == TeamMembership.organisation_membership_id,
        )
        .where(
            Team.organisation_id == organisation_id,
            Team.is_active.is_(True),
            TeamMembership.organisation_id == organisation_id,
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.role == "AGENT",
            OrganisationMembership.is_active.is_(True),
        )
        .distinct()
        .order_by(Team.name)
    ).all()

    if not eligible_teams:
        return {
            "team_id": None,
            "team_name": None,
            "confidence": 0,
            "explanation": (
                "No active team with an active AGENT membership "
                "is available in this organisation."
            ),
        }

    if len(eligible_teams) == 1:
        team = eligible_teams[0]

        return {
            "team_id": team.id,
            "team_name": team.name,
            "confidence": 60,
            "explanation": (
                f"{team.name} is the only active team with an "
                "active AGENT membership in this organisation."
            ),
        }

    if not category_name:
        return {
            "team_id": None,
            "team_name": None,
            "confidence": 0,
            "explanation": (
                "Multiple eligible teams were found, but no ticket "
                "category is available to compare their expertise."
            ),
        }

    category_key = category_name.casefold()
    category_keywords = CATEGORY_KEYWORDS.get(category_key, [])

    if not category_keywords:
        return {
            "team_id": None,
            "team_name": None,
            "confidence": 0,
            "explanation": (
                f"No expertise keywords are configured for "
                f"the {category_name} category."
            ),
        }

    team_scores = []

    for team in eligible_teams:
        description = normalize_ticket_text("", team.description or "")
        matches = keyword_matches(description, category_keywords)

        team_scores.append(
            {
                "team": team,
                "score": len(matches),
                "matches": matches,
            }
        )

    highest_score = max(item["score"] for item in team_scores)

    if highest_score == 0:
        return {
            "team_id": None,
            "team_name": None,
            "confidence": 0,
            "explanation": (
                f"No eligible team description matched the "
                f"{category_name} category expertise keywords."
            ),
        }

    best_teams = [item for item in team_scores if item["score"] == highest_score]

    if len(best_teams) > 1:
        return {
            "team_id": None,
            "team_name": None,
            "confidence": 0,
            "explanation": (
                f"Multiple teams have matching expertise for "
                f"{category_name}. A reliable recommendation "
                f"cannot be made."
            ),
        }

    best_match = best_teams[0]
    team = best_match["team"]
    matches = best_match["matches"]

    confidence = min(85, 60 + (highest_score - 1) * 10)

    return {
        "team_id": team.id,
        "team_name": team.name,
        "confidence": confidence,
        "explanation": (
            f"{team.name} is recommended for {category_name} tickets. "
            f"Its team description contains {len(matches)} matching "
            f"expertise keyword(s): {', '.join(matches)}. "
            "It had the strongest unique expertise match among "
            "the eligible teams."
        ),
    }


def classify_ticket(
    db: Session,
    organisation_id,
    subject: str,
    description: str,
) -> dict:
    """
    Generate explainable ticket classification suggestions.

    This function does not create or modify tickets.
    """

    categories = db.scalars(
        select(Category).where(
            Category.organisation_id == organisation_id,
            Category.is_active.is_(True),
        )
    ).all()

    category_result = suggest_category(
        subject=subject,
        description=description,
        categories=categories,
    )

    impact_result = suggest_impact(
        subject=subject,
        description=description,
    )

    urgency_result = suggest_urgency(
        subject=subject,
        description=description,
    )

    priority = None

    if impact_result["value"] and urgency_result["value"]:
        priority = calculate_ticket_priority(
            impact=impact_result["value"],
            urgency=urgency_result["value"],
        )

    team_result = suggest_team(
        db=db,
        organisation_id=organisation_id,
        category_name=category_result["category_name"],
    )

    # Add confidence levels to each suggestion.
    category_result["confidence_level"] = get_confidence_level(
        category_result["confidence"]
    )
    impact_result["confidence_level"] = get_confidence_level(
        impact_result["confidence"]
    )
    urgency_result["confidence_level"] = get_confidence_level(
        urgency_result["confidence"]
    )
    team_result["confidence_level"] = get_confidence_level(team_result["confidence"])

    # Calculate overall confidence using category, impact, and urgency.
    classification_confidences = [
        category_result["confidence"],
        impact_result["confidence"],
        urgency_result["confidence"],
    ]

    overall_confidence = round(
        sum(classification_confidences) / len(classification_confidences)
    )

    # Identify suggestions that need human review.
    fields_requiring_review = [
        field_name
        for field_name, result in [
            ("category", category_result),
            ("impact", impact_result),
            ("urgency", urgency_result),
            ("team", team_result),
        ]
        if result["confidence"] < 70
    ]

    return {
        "category": category_result,
        "impact": impact_result,
        "urgency": urgency_result,
        "priority": priority,
        "team": team_result,
        "requires_human_review": True,
        "overall_confidence": overall_confidence,
        "fields_requiring_review": fields_requiring_review,
        "confidence_type": "heuristic",
    }
