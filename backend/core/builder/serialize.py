from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def coerce_builder_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize DB row values for Pydantic models expecting JSON-friendly types."""
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (datetime, date)):
            out[key] = value.isoformat()
        elif isinstance(value, UUID):
            out[key] = str(value)
        elif isinstance(value, Decimal):
            out[key] = float(value)
        elif isinstance(value, bytes):
            out[key] = value.decode("utf-8")
        else:
            out[key] = value
    return out
