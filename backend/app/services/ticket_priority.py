def calculate_ticket_priority(
    impact: str,
    urgency: str,
) -> str:
    """Calculate ticket priority from impact and urgency."""

    priority_matrix = {
        ("HIGH", "HIGH"): "P1",
        ("HIGH", "MEDIUM"): "P2",
        ("HIGH", "LOW"): "P2",
        ("MEDIUM", "HIGH"): "P2",
        ("MEDIUM", "MEDIUM"): "P3",
        ("MEDIUM", "LOW"): "P3",
        ("LOW", "HIGH"): "P3",
        ("LOW", "MEDIUM"): "P4",
        ("LOW", "LOW"): "P4",
    }

    return priority_matrix[(impact, urgency)]
