import re

from app.services.ai.confidence import (
    calculate_category_confidence,
    calculate_field_confidence,
)
from app.services.ai.text_preprocessing import normalize_ticket_text

CATEGORY_KEYWORDS = {
    "network": [
        "wifi",
        "wi-fi",
        "internet",
        "network",
        "vpn",
        "connectivity",
        "connection timeout",
        "router",
        "dns",
        "ethernet",
        "firewall",
        "packet loss",
    ],
    "hardware": [
        "laptop",
        "desktop",
        "computer",
        "monitor",
        "keyboard",
        "mouse",
        "printer",
        "battery",
        "hard drive",
        "ssd",
        "ram",
        "overheating",
        "device",
    ],
    "software": [
        "software",
        "application",
        "business application",
        "business applications",
        "application outage",
        "app crash",
        "installation",
        "install",
        "update",
        "upgrade",
        "bug",
        "exception",
        "error message",
        "windows",
        "driver",
    ],
    "account & access": [
        "login",
        "log in",
        "sign in",
        "password",
        "reset password",
        "account locked",
        "locked out",
        "permission",
        "access denied",
        "authentication",
        "authorization",
        "mfa",
        "two factor",
    ],
    "email & collaboration": [
        "email",
        "outlook",
        "mailbox",
        "calendar",
        "teams meeting",
        "video meeting",
        "collaboration",
        "chat message",
        "email attachment",
        "mail server",
    ],
    "security": [
        "security",
        "phishing",
        "malware",
        "ransomware",
        "virus",
        "antivirus",
        "suspicious activity",
        "data breach",
        "unauthorized access",
        "vulnerability",
        "endpoint protection",
    ],
}
CATEGORY_KEYWORD_WEIGHTS = {
    "security": {
        "phishing": 3,
        "malware": 3,
        "ransomware": 3,
        "virus": 3,
        "data breach": 3,
        "unauthorized access": 3,
        "suspicious activity": 2,
        "security": 1,
    },
}


def keyword_matches(text: str, keywords: list[str]) -> list[str]:
    """Return keywords found as whole words or phrases."""

    matches = []

    for keyword in keywords:
        pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"

        if re.search(pattern, text):
            matches.append(keyword)

    return matches


def suggest_category(
    subject: str,
    description: str,
    categories: list,
) -> dict:
    """
    Suggest a category using explainable keyword matching.

    Categories must come from the current organisation's
    active database categories.

    This function never modifies a ticket.
    """

    normalized_text = normalize_ticket_text(subject, description)

    if not normalized_text:
        raise ValueError("Ticket subject and description cannot both be empty.")

    predictions = []

    for category in categories:
        category_name = category.name.strip()
        category_key = category_name.casefold()

        keywords = CATEGORY_KEYWORDS.get(category_key, [])

        matches = keyword_matches(normalized_text, keywords)

        if matches:
            predictions.append(
                {
                    "category_id": category.id,
                    "category_name": category_name,
                    "score": sum(
                        CATEGORY_KEYWORD_WEIGHTS.get(category_key, {}).get(keyword, 1)
                        for keyword in matches
                    ),
                    "matched_keywords": matches,
                }
            )

    # Sort by score, then category name for deterministic results.
    predictions.sort(
        key=lambda item: (-item["score"], item["category_name"].casefold())
    )

    # No known category keywords matched.
    if not predictions:
        other_category = next(
            (
                category
                for category in categories
                if category.name.strip().casefold() == "other"
            ),
            None,
        )

        if other_category is None:
            return {
                "category_id": None,
                "category_name": None,
                "confidence": 0,
                "matched_keywords": [],
                "explanation": "No matching category rules were found.",
            }

        return {
            "category_id": other_category.id,
            "category_name": other_category.name,
            "confidence": 25,
            "matched_keywords": [],
            "explanation": (
                "No known category keywords matched. Other is suggested as a fallback."
            ),
        }

    best_prediction = predictions[0]
    best_score = best_prediction["score"]

    # This is a heuristic score, not a statistically calibrated probability.
    second_score = predictions[1]["score"] if len(predictions) > 1 else None

    confidence = calculate_category_confidence(
        best_score=best_score,
        second_score=second_score,
    )
    explanation = (
        f"Suggested {best_prediction['category_name']} because "
        f"the ticket contains matching keywords: "
        f"{', '.join(best_prediction['matched_keywords'])}."
    )

    if second_score == best_score:
        explanation += (
            " Another category received the same keyword score, "
            "so this suggestion needs human review."
        )
    elif second_score is not None and second_score >= best_score - 1:
        explanation += (
            " Another category received a similar keyword score, "
            "so this suggestion has some uncertainty."
        )
    else:
        explanation += " This category had the strongest keyword match."

    return {
        "category_id": best_prediction["category_id"],
        "category_name": best_prediction["category_name"],
        "confidence": confidence,
        "matched_keywords": best_prediction["matched_keywords"],
        "explanation": explanation,
    }


IMPACT_RULES = {
    "HIGH": [
        "all users",
        "all employees",
        "all staff",
        "everyone",
        "company-wide",
        "entire company",
        "entire organisation",
        "production down",
        "production server down",
        "business stopped",
        "critical system",
        "critical business outage",
        "critical business applications",
        "multiple departments",
    ],
    "MEDIUM": [
        "multiple users",
        "team affected",
        "intermittent",
        "partially working",
        "slow performance",
        "degraded",
    ],
    "LOW": [
        "single user",
        "one user",
        "minor issue",
        "cosmetic",
        "how to",
        "general question",
    ],
}


URGENCY_RULES = {
    "HIGH": [
        "production down",
        "production server down",
        "business stopped",
        "cannot work",
        "completely unavailable",
        "security breach",
        "ransomware",
        "data breach",
        "urgent",
        "immediately",
        "immediate attention",
        "critical",
        "critical business outage",
    ],
    "MEDIUM": [
        "intermittent",
        "partially working",
        "workaround",
        "degraded",
        "affecting work",
        "performance issue",
    ],
    "LOW": [
        "general question",
        "how to",
        "minor issue",
        "cosmetic",
        "when possible",
        "information request",
    ],
}


def suggest_impact(subject: str, description: str) -> dict:
    """Suggest business impact using explainable keyword rules."""

    text = normalize_ticket_text(subject, description)

    matches = {
        level: keyword_matches(text, keywords)
        for level, keywords in IMPACT_RULES.items()
    }

    best_level = max(
        matches,
        key=lambda level: (len(matches[level]), level == "HIGH"),
    )

    if not matches[best_level]:
        return {
            "value": None,
            "confidence": 0,
            "matched_keywords": [],
            "explanation": (
                "There is insufficient information to determine the business impact."
            ),
        }

    has_conflicting_indicators = sum(bool(value) for value in matches.values()) > 1

    confidence = calculate_field_confidence(
        matched_keyword_count=len(matches[best_level]),
        has_conflicting_indicators=has_conflicting_indicators,
    )

    if has_conflicting_indicators:
        conflicting_levels = [level for level, keywords in matches.items() if keywords]

        explanation = (
            f"Conflicting impact indicators were found. "
            f"{best_level} impact suggested based on: "
            f"{', '.join(matches[best_level])}. "
            f"Indicators for {', '.join(conflicting_levels)} "
            "impact were also detected. Human review is recommended."
        )
    else:
        explanation = (
            f"{best_level} impact suggested because the ticket mentions: "
            f"{', '.join(matches[best_level])}. "
            f"These indicators match the {best_level} impact rules."
        )

    return {
        "value": best_level,
        "confidence": confidence,
        "matched_keywords": matches[best_level],
        "explanation": explanation,
    }


def suggest_urgency(subject: str, description: str) -> dict:
    """Suggest urgency using explainable keyword rules."""

    text = normalize_ticket_text(subject, description)

    matches = {
        level: keyword_matches(text, keywords)
        for level, keywords in URGENCY_RULES.items()
    }

    best_level = max(
        matches,
        key=lambda level: (len(matches[level]), level == "HIGH"),
    )

    if not matches[best_level]:
        return {
            "value": None,
            "confidence": 0,
            "matched_keywords": [],
            "explanation": (
                "There is insufficient information to determine the urgency."
            ),
        }

    has_conflicting_indicators = sum(bool(value) for value in matches.values()) > 1

    confidence = calculate_field_confidence(
        matched_keyword_count=len(matches[best_level]),
        has_conflicting_indicators=has_conflicting_indicators,
    )

    if has_conflicting_indicators:
        conflicting_levels = [level for level, keywords in matches.items() if keywords]

        explanation = (
            f"Conflicting urgency indicators were found. "
            f"{best_level} urgency suggested based on: "
            f"{', '.join(matches[best_level])}. "
            f"Indicators for {', '.join(conflicting_levels)} "
            "urgency were also detected. Human review is recommended."
        )
    else:
        explanation = (
            f"{best_level} urgency suggested because the ticket mentions: "
            f"{', '.join(matches[best_level])}. "
            f"These indicators match the {best_level} urgency rules."
        )
    return {
        "value": best_level,
        "confidence": confidence,
        "matched_keywords": matches[best_level],
        "explanation": explanation,
    }
