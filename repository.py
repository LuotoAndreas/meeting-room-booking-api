from __future__ import annotations

from threading import Lock
from typing import Dict, List

from models import Booking, intervals_overlap


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._items: Dict[str, Booking] = {}
        self._lock = Lock()

    def list_by_room(self, room_id: str) -> List[Booking]:
        with self._lock:
            return [b for b in self._items.values() if b.room_id == room_id]

    # The old get_all bookings method that is no longer used for now
    def get_all(self) -> List[Booking]:
        with self._lock:
            return list(self._items.values())

    # The old insert method that is no longer used for now
    def insert(self, booking: Booking) -> None:
        with self._lock:
            self._items[booking.booking_id] = booking
    
    # New method to insert booking if no overlap exists
    def insert_if_no_overlap(self, booking: Booking) -> bool:
         """
        Atomically checks overlap and inserts the booking if possible.
        Returns True if inserted, False if overlap exists.
        """
         with self._lock:
            for existing in self._items.values():
                if existing.room_id != booking.room_id:
                    continue

                if intervals_overlap(
                    booking.start_utc,
                    booking.end_utc,
                    existing.start_utc,
                    existing.end_utc,
                ):
                    return False

            self._items[booking.booking_id] = booking
            return True

    def delete(self, booking_id: str) -> bool:
        with self._lock:
            if booking_id not in self._items:
                return False
            del self._items[booking_id]
            return True

    def reset(self) -> None:
        """Clear all bookings. For testing only."""
        with self._lock:
            self._items.clear()
       