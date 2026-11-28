def calculate_category_confidence(
    best_score: int,
    second_score: int | None = None,
) -> int:
    """Calculate heuristic confidence for category suggestions."""

    if best_score <= 0:
        return 0

    confidence = min(85, 55 + (best_score - 1) * 10)

    if second_score is not None:
        if second_score == best_score:
            confidence = min(confidence, 45)
        elif second_score >= best_score - 1:
            confidence = max(40, confidence - 10)

    return confidence


def calculate_field_confidence(
    matched_keyword_count: int,
    has_conflicting_indicators: bool = False,
) -> int:
    """Calculate heuristic confidence for impact and urgency."""

    if matched_keyword_count <= 0:
        return 0

    if has_conflicting_indicators:
        return 40

    return min(80, 55 + matched_keyword_count * 10)


def get_confidence_level(confidence: int) -> str:
    """Convert a heuristic confidence score into a readable level."""

    if confidence < 40:
        return "LOW"

    if confidence < 70:
        return "MODERATE"

    return "HIGH"
