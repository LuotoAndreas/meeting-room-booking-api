from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


# -----------------------------
# Shared time helpers
# -----------------------------
def parse_iso8601_tz(ts: str) -> datetime:
    """
    Parse ISO-8601 timestamp with timezone into an aware datetime.
    Accepts 'Z' suffix by converting it to '+00:00'.
    """
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError("timestamp must be a non-empty string")

    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    dt = datetime.fromisoformat(s)  # expects offset like +02:00 or +00:00
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must include a timezone offset")
    return dt


def to_utc(dt: datetime) -> datetime:
    # dt is aware
    return dt.astimezone(timezone.utc)


def intervals_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """
    Half-open interval overlap: [start, end)
    Overlap iff a_start < b_end AND b_start < a_end.
    Back-to-back is allowed (end == other.start is NOT overlap).
    """
    return a_start < b_end and b_start < a_end


def utc_iso_z(dt: datetime) -> str:
    # dt is aware, UTC
    return dt.isoformat().replace("+00:00", "Z")


# -----------------------------
# API models (transport layer)
# -----------------------------
class CreateBookingIn(BaseModel):
    room_id: str = Field(..., min_length=1)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def must_be_iso8601_with_tz(cls, v: str) -> str:
        # Validate format + timezone presence early; actual comparison happens in service.
        parse_iso8601_tz(v)
        return v


class BookingOut(BaseModel):
    booking_id: str
    room_id: str
    start: str  # ISO-8601 with timezone (we return UTC with Z)
    end: str


# -----------------------------
# Domain model
# -----------------------------
@dataclass(frozen=True)
class Booking:
    booking_id: str
    room_id: str
    start_utc: datetime  # aware, UTC
    end_utc: datetime    # aware, UTC
