import re
import unicodedata


def normalize_ticket_text(subject: str, description: str) -> str:
    """
    Normalize ticket subject and description for AI classification.

    This function preserves useful technical information such as:
    - Wi-Fi
    - VPN
    - Windows 11
    - HTTP 500
    - Error codes
    """

    combined_text = f"{subject} {description}"

    # Normalize Unicode characters.
    normalized_text = unicodedata.normalize("NFKC", combined_text)

    # Convert text to lowercase.
    normalized_text = normalized_text.lower()

    # Remove URLs.
    normalized_text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        normalized_text,
    )

    # Replace repeated whitespace with a single space.
    normalized_text = re.sub(r"\s+", " ", normalized_text)

    return normalized_text.strip()
