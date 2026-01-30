from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from models import (
    Booking,
    BookingOut,
    CreateBookingIn,
    parse_iso8601_tz,
    to_utc,
    utc_iso_z,
)
from repository import InMemoryBookingRepository


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

        # Rule: no overlap with existing bookings in the same room
        booking_id = f"bkg_{uuid4().hex}"
        booking = Booking(
            booking_id=booking_id,
            room_id=payload.room_id,
            start_utc=start,
            end_utc=end,
        )

        inserted = self._repo.insert_if_no_overlap(booking)
        if not inserted:
            raise OverlapConflictError()

        return BookingOut(
            booking_id=booking.booking_id,
            room_id=booking.room_id,
            start=utc_iso_z(booking.start_utc),
            end=utc_iso_z(booking.end_utc),
        )

    def delete_booking(self, booking_id: str) -> None:
        deleted = self._repo.delete(booking_id)
        if not deleted:
            raise BookingNotFoundError()

    def list_bookings_for_room(self, room_id: str):
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
