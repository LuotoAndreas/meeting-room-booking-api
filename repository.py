from __future__ import annotations

from threading import Lock
from typing import Dict, List

from models import Booking


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

    def reset(self) -> None:
        """Clear all bookings. For testing only."""
        with self._lock:
            self._items.clear()
       