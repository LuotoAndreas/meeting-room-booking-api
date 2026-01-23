from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel, Field, field_validator


app = FastAPI(title="Meeting Room Booking API", version="1.0.0")


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


class CreateBookingIn(BaseModel):
    room_id: str = Field(..., min_length=1)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def must_be_iso8601_with_tz(cls, v: str) -> str:
        # Validate format + timezone presence early; actual comparison happens in endpoint.
        parse_iso8601_tz(v)
        return v


class BookingOut(BaseModel):
    booking_id: str
    room_id: str
    start: str  # ISO-8601 with timezone (we return UTC with Z)
    end: str


@dataclass(frozen=True)
class Booking:
    booking_id: str
    room_id: str
    start_utc: datetime  # aware, UTC
    end_utc: datetime    # aware, UTC


# In-memory store: booking_id -> Booking
BOOKINGS: Dict[str, Booking] = {}
LOCK = Lock()


@app.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: CreateBookingIn) -> BookingOut:
    start = to_utc(parse_iso8601_tz(payload.start))
    end = to_utc(parse_iso8601_tz(payload.end))

    # Rule: start must be before end
    if not (start < end):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validation error: start must be before end.",
        )

    # Rule: bookings cannot be in the past (start >= now)
    now = datetime.now(timezone.utc)
    if start < now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validation error: booking start cannot be in the past.",
        )

    # Rule: bookings for the same room must not overlap (half-open intervals)
    with LOCK:
        for b in BOOKINGS.values():
            if b.room_id != payload.room_id:
                continue
            if intervals_overlap(start, end, b.start_utc, b.end_utc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Overlap conflict: booking overlaps an existing booking in this room.",
                )

        booking_id = f"bkg_{uuid4().hex}"
        BOOKINGS[booking_id] = Booking(
            booking_id=booking_id,
            room_id=payload.room_id,
            start_utc=start,
            end_utc=end,
        )

    # Return UTC timestamps using 'Z'
    return BookingOut(
        booking_id=booking_id,
        room_id=payload.room_id,
        start=start.isoformat().replace("+00:00", "Z"),
        end=end.isoformat().replace("+00:00", "Z"),
    )


@app.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(booking_id: str = Path(..., min_length=1)) -> None:
    # Cancellation is a hard delete.
    with LOCK:
        if booking_id not in BOOKINGS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found.",
            )
        del BOOKINGS[booking_id]
    return None


@app.get("/rooms/{room_id}/bookings", response_model=List[BookingOut])
def list_bookings_for_room(room_id: str = Path(..., min_length=1)) -> List[BookingOut]:
    with LOCK:
        items = [b for b in BOOKINGS.values() if b.room_id == room_id]

    # Sort by start time ascending
    items.sort(key=lambda b: b.start_utc)

    return [
        BookingOut(
            booking_id=b.booking_id,
            room_id=b.room_id,
            start=b.start_utc.isoformat().replace("+00:00", "Z"),
            end=b.end_utc.isoformat().replace("+00:00", "Z"),
        )
        for b in items
    ]
