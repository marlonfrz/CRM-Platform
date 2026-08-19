def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if not normalized or "@" not in normalized:
        raise ValueError("A valid email address is required")
    return normalized


def normalize_name(name: str) -> str:
    normalized = " ".join(name.strip().split())
    if not normalized:
        raise ValueError("A name is required")
    return normalized
