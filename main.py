from __future__ import annotations

from fastapi import FastAPI

from api import create_router
from repository import InMemoryBookingRepository
from services import BookingService

app = FastAPI(title="Meeting Room Booking API", version="1.0.0")

# Wire up dependencies (still in-memory; behavior unchanged)
_repo = InMemoryBookingRepository()
_service = BookingService(_repo)

# Register routes
app.include_router(create_router(_service))
