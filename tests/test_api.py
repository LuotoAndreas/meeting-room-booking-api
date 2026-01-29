from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_booking_success():
    response = client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2030-01-01T10:00:00Z",
            "end": "2030-01-01T11:00:00Z"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["room_id"] == "room_1"
    assert data["start"] == "2030-01-01T10:00:00Z"
    assert data["end"] == "2030-01-01T11:00:00Z"

def test_create_booking_start_not_before_end():
    response = client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2030-01-01T12:00:00Z",
            "end": "2030-01-01T11:00:00Z"
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Validation error: start must be before end."

def test_create_booking_start_in_past():
    response = client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2000-01-01T10:00:00Z",
            "end": "2000-01-01T11:00:00Z"
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Validation error: booking start cannot be in the past."

def test_create_booking_overlap_conflict():
    # First booking
    client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2030-01-01T10:00:00Z",
            "end": "2030-01-01T11:00:00Z"
        }
    )
    # Overlapping booking
    response = client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2030-01-01T10:30:00Z",
            "end": "2030-01-01T11:30:00Z"
        }
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Overlap conflict: booking overlaps an existing booking in this room."

def test_create_booking_back_to_back_no_conflict():
    # First booking
    client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2030-01-01T10:00:00Z",
            "end": "2030-01-01T11:00:00Z"
        }
    )
    # Back-to-back booking
    response = client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2030-01-01T11:00:00Z",
            "end": "2030-01-01T12:00:00Z"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["room_id"] == "room_1"
    assert data["start"] == "2030-01-01T11:00:00Z"
    assert data["end"] == "2030-01-01T12:00:00Z"

def test_create_booking_invalid_timestamp():
    response = client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2030-01-01T10:00:00",  # Missing timezone
            "end": "2030-01-01T11:00:00Z"
        }
    )
    assert response.status_code == 422

def test_same_time_different_rooms_no_conflict():
    # Booking in room_1
    client.post(
        "/bookings",
        json={
            "room_id": "room_1",
            "start": "2030-01-01T10:00:00Z",
            "end": "2030-01-01T11:00:00Z"
        }
    )
    # Same time booking in room_2
    response = client.post(
        "/bookings",
        json={
            "room_id": "room_2",
            "start": "2030-01-01T10:00:00Z",
            "end": "2030-01-01T11:00:00Z"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["room_id"] == "room_2"
    assert data["start"] == "2030-01-01T10:00:00Z"
    assert data["end"] == "2030-01-01T11:00:00Z"

def test_list_bookings_for_room():
    # Create bookings for room_3
    client.post(
        "/bookings",
        json={
            "room_id": "room_3",
            "start": "2030-01-03T10:00:00Z",
            "end": "2030-01-03T11:00:00Z"
        }
    )
    client.post(
        "/bookings",
        json={
            "room_id": "room_3",
            "start": "2030-01-03T12:00:00Z",
            "end": "2030-01-03T13:00:00Z"
        }
    )

    response = client.get("/rooms/room_3/bookings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["room_id"] == "room_3"
    assert data[1]["room_id"] == "room_3"

def test_delete_booking_success():
    # Create a booking to delete
    response = client.post(
        "/bookings",
        json={
            "room_id": "room_2",
            "start": "2030-01-02T10:00:00Z",
            "end": "2030-01-02T11:00:00Z"
        }
    )
    booking_id = response.json()["booking_id"]

    # Delete the booking
    delete_response = client.delete(f"/bookings/{booking_id}")
    assert delete_response.status_code == 204

def test_delete_booking_not_found():
    response = client.delete("/bookings/non_existent_booking")
    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found."
