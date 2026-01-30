from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Path, status

from models import BookingOut, CreateBookingIn
from services import (
    BookingNotFoundError,
    BookingService,
    OverlapConflictError,
    StartInPastError,
    StartNotBeforeEndError,
)


def create_router(service: BookingService) -> APIRouter:
    router = APIRouter()

    @router.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
    def create_booking(payload: CreateBookingIn) -> BookingOut:
        try:
            return service.create_booking(payload)
        except StartNotBeforeEndError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Validation error: start must be before end.",
            )
        except StartInPastError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Validation error: booking start cannot be in the past.",
            )
        except OverlapConflictError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Overlap conflict: booking overlaps an existing booking in this room.",
            )

    @router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_booking(booking_id: str = Path(..., min_length=1)) -> None:
        try:
            service.delete_booking(booking_id)
            return None
        except BookingNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found.",
            )

    @router.get("/rooms/{room_id}/bookings", response_model=List[BookingOut])
    def list_bookings_for_room(room_id: str = Path(..., min_length=1)) -> List[BookingOut]:
        return service.list_bookings_for_room(room_id)

    return router
