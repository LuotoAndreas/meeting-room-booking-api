from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel, Field, field_validator


app = FastAPI(title="Meeting Room Booking API", version="1.0.0")


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


# -----------------------------
# Repository (storage + locking)
# -----------------------------
class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._items: Dict[str, Booking] = {}
        self._lock = Lock()

    def list_by_room(self, room_id: str) -> List[Booking]:
        with self._lock:
            return [b for b in self._items.values() if b.room_id == room_id]

    def get_all(self) -> List[Booking]:
        with self._lock:
            return list(self._items.values())

    def insert(self, booking: Booking) -> None:
        with self._lock:
            self._items[booking.booking_id] = booking

    def delete(self, booking_id: str) -> bool:
        with self._lock:
            if booking_id not in self._items:
                return False
            del self._items[booking_id]
            return True


# -----------------------------
# Service layer (business rules)
# -----------------------------
class BookingError(Exception):
    """Base class for domain/service errors."""


class StartNotBeforeEndError(BookingError):
    pass


class StartInPastError(BookingError):
    pass


class OverlapConflictError(BookingError):
    pass


class BookingNotFoundError(BookingError):
    pass


class BookingService:
    def __init__(self, repo: InMemoryBookingRepository) -> None:
        self._repo = repo

    def create_booking(self, payload: CreateBookingIn) -> BookingOut:
        start = to_utc(parse_iso8601_tz(payload.start))
        end = to_utc(parse_iso8601_tz(payload.end))

        # Rule: start must be before end
        if not (start < end):
            raise StartNotBeforeEndError()

        # Rule: bookings cannot be in the past (start >= now)
        now = datetime.now(timezone.utc)
        if start < now:
            raise StartInPastError()

        # Rule: bookings for the same room must not overlap (half-open intervals)
        # NOTE: To preserve behavior, we compare against current in-memory state.
        for b in self._repo.get_all():
            if b.room_id != payload.room_id:
                continue
            if intervals_overlap(start, end, b.start_utc, b.end_utc):
                raise OverlapConflictError()

        booking_id = f"bkg_{uuid4().hex}"
        booking = Booking(
            booking_id=booking_id,
            room_id=payload.room_id,
            start_utc=start,
            end_utc=end,
        )
        self._repo.insert(booking)

        return BookingOut(
            booking_id=booking.booking_id,
            room_id=booking.room_id,
            start=utc_iso_z(booking.start_utc),
            end=utc_iso_z(booking.end_utc),
        )

    def delete_booking(self, booking_id: str) -> None:
        # Cancellation is a hard delete.
        deleted = self._repo.delete(booking_id)
        if not deleted:
            raise BookingNotFoundError()

    def list_bookings_for_room(self, room_id: str) -> List[BookingOut]:
        items = self._repo.list_by_room(room_id)
        items.sort(key=lambda b: b.start_utc)

        return [
            BookingOut(
                booking_id=b.booking_id,
                room_id=b.room_id,
                start=utc_iso_z(b.start_utc),
                end=utc_iso_z(b.end_utc),
            )
            for b in items
        ]


# Wire up dependencies (still in-memory; behavior unchanged)
_repo = InMemoryBookingRepository()
_service = BookingService(_repo)


# -----------------------------
# API routes (minimal work)
# -----------------------------
@app.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: CreateBookingIn) -> BookingOut:
    try:
        return _service.create_booking(payload)
    except StartNotBeforeEndError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validation error: start must be before end.",
        )
    except StartInPastError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validation error: booking start cannot be in the past.",
        )
    except OverlapConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Overlap conflict: booking overlaps an existing booking in this room.",
        )


@app.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(booking_id: str = Path(..., min_length=1)) -> None:
    try:
        _service.delete_booking(booking_id)
        return None
    except BookingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )


@app.get("/rooms/{room_id}/bookings", response_model=List[BookingOut])
def list_bookings_for_room(room_id: str = Path(..., min_length=1)) -> List[BookingOut]:
    return _service.list_bookings_for_room(room_id)
