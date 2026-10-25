"""Validation helpers shared by paginated monitoring endpoints."""

from typing import Optional, Tuple


def parse_pagination(
    limit_value: str | None,
    offset_value: str | None,
    max_limit: int = 200,
) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """Parse and validate limit/offset query parameters."""
    try:
        limit = int(limit_value) if limit_value is not None else 50
        offset = int(offset_value) if offset_value is not None else 0
    except (TypeError, ValueError):
        return None, None, "limit and offset must be integers."

    if limit < 1 or limit > max_limit:
        return None, None, f"limit must be between 1 and {max_limit}."
    if offset < 0:
        return None, None, "offset must be zero or greater."

    return limit, offset, None
