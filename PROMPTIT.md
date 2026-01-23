Promptihistoria ChatGPT:n kanssa.
Käytin ChatGPT:tä englanniksi, koska koen saavani sillä tarkempia ja luotettavampia vastauksia. Lähestymistapani oli ensin käyttää tekoälyä varmentamaan muutamia esikysymyksiä (esim. aikakäsittely, päällekkäisyyksien estäminen ja HTTP-statuskoodit) ennen varsinaisten toteutuspromptien kirjoittamista. Näiden pohjalta pystyin laatimaan selkeät ja rajatut promptit itse ohjelman tuottamista varten. Varsinainen koodin generointi tehtiin vasta tämän jälkeen mikä mielestäni vähentää korjausta vaativia bugeja huomattavasti. 

-------------------------------------------------------------------------------------------------------------------------------------
## 1. Esikysymykset ennen varsinaisia prompteja: Aikakäsittely, varausten aikavälit sekä HTTP-statuskoodit varausrajapinnassa.
-------------------------------------------------------------------------------------------------------------------------------------
### Prompti: 

I'm designing a simple meeting room booking API. I want to avoid common bugs and overengineering, especially around time handling and booking conflicts. What are the best practices and default choices I should use for representing time and defining booking intervals, and why are they recommended? Keep the answer brief.

-------------------------------------------------------------------------------------------------------------------------------------
### AI-vastaus: 
Best-practice defaults for a simple booking API:

Represent time as UTC timestamps (ISO-8601 with timezone offset on input/output).
Why: avoids timezone and daylight-saving bugs, keeps storage and comparisons consistent, and makes DB queries reliable.

Define bookings as half-open intervals
[start,end).
Why: prevents edge-case conflicts—one booking ending at 10:00 and another starting at 10:00 do not overlap—simplifying conflict checks and reasoning.

Together, these two choices eliminate most subtle time-handling and double-booking bugs without adding complexity.

-------------------------------------------------------------------------------------------------------------------------------------
### Prompti: 

Explain which HTTP status codes should I use in a simple meeting room booking API. Cover the following operations: creating a booking, cancelling a booking, retrieving (listing) all bookings. For each operation: list the most appropriate status codes, explain shortly when each code should be returned, mention common alternatives if they exist and why one is preferred. Keep the explanation short and focused on best practices. Do not add features other than basic booking, cancellation, listing, validation, and conflict handling. Make it brief.

-------------------------------------------------------------------------------------------------------------------------------------
### AI-vastaus: 

Create a booking — POST /bookings
  201 Created: booking successfully created (often include the created booking and/or Location header).
  409 Conflict: time overlap with an existing booking for the same room (your business conflict).
  422 Unprocessable Entity: validation fails (missing fields, bad timestamp format, end <= start).
    Alternative: 400 Bad Request is also common for validation. Prefer 422 if you want to clearly separate “well-formed request but invalid data” from generic bad requests—either is fine if you’re consistent.
  404 Not Found (optional): if room_id refers to a room that doesn’t exist (if you model rooms).

Cancel a booking — DELETE /bookings/{id}
  204 No Content: successfully cancelled/deleted (no response body).
    Alternative: 200 OK if you return the cancelled booking in the body.
  404 Not Found: booking id doesn’t exist.
  409 Conflict (less common here): only if your rules prevent cancellation in some state (often avoid this in a minimal system).

List all bookings — GET /bookings
  200 OK: returns a list (possibly empty).
  Alternative: 204 No Content for an empty list is sometimes used, but 200 with [] is generally preferred because it’s simpler and consistent for clients.
Minimal best-practice set to implement: 201, 200, 204, 404, 409, and either 422 or 400 for validation (pick one and use it everywhere).

-------------------------------------------------------------------------------------------------------------------------------------
## OMAT OLETUKSET: 
  Päätin käyttää toteutuksessa ISO-8601-aikaleimoja aikavyöhyketiedolla ja mallintaa varaukset aikaväleinä [start, end), jotta peräkkäiset varaukset ovat sallittuja ilman päällekkäisyysongelmia. Käytän 422-validointivirheisiin ja 409-päällekkäisyystilanteisiin, jotta virhetilanteet ovat asiakkaalle selkeitä ja yhdenmukaisia. Koska tallennus on in-memory, kaikki data häviää jos palvelimen käynnistää uudestaan.
  
## 2. Toteutus: API-suunnitelma: 
-------------------------------------------------------------------------------------------------------------------------------------
### Prompti

Propose a minimal API design for meeting room bookings. It needs to: create booking, cancel booking, list bookings for a room. Also list the assumptions you are making (time format, timezone, overlap definition including back-to-back bookings, cancellation behavior and booking id).

-------------------------------------------------------------------------------------------------------------------------------------
### AI-vastaus

Minimal API (REST, JSON)

Base URL: /v1

1) Create booking
POST /rooms/{roomId}/bookings
Request

{
  "start": "2026-01-20T10:00:00Z",
  "end": "2026-01-20T11:00:00Z",
  "title": "Team sync",
  "createdBy": "user-123"
}

Responses
201 Created

{
  "bookingId": "bkg_01HTYQ9Y2QK5W3B2Z8JZ6V7N8M",
  "roomId": "room-42",
  "start": "2026-01-20T10:00:00Z",
  "end": "2026-01-20T11:00:00Z",
  "title": "Team sync",
  "createdBy": "user-123",
  "status": "active",
  "createdAt": "2026-01-20T09:12:33Z"
}

409 Conflict (overlap)

{
  "error": "overlap",
  "message": "Booking overlaps with an existing booking.",
  "conflictsWith": ["bkg_01HTYQ8..."]
}

400 Bad Request (invalid time range, missing fields, etc.)

2) Cancel booking
DELETE /bookings/{bookingId}
Response
204 No Content (successful)
404 Not Found (unknown booking)
(Optional if you want cancellation metadata back instead of 204: return 200 with the updated booking object.)

3) List bookings for a room
GET /rooms/{roomId}/bookings?from=2026-01-20T00:00:00Z&to=2026-01-27T00:00:00Z
Response
200 OK

{
  "roomId": "room-42",
  "from": "2026-01-20T00:00:00Z",
  "to": "2026-01-27T00:00:00Z",
  "bookings": [
    {
      "bookingId": "bkg_01HTYQ9Y2QK5W3B2Z8JZ6V7N8M",
      "start": "2026-01-20T10:00:00Z",
      "end": "2026-01-20T11:00:00Z",
      "title": "Team sync",
      "createdBy": "user-123",
      "status": "active"
    }
  ]
}

Notes:
from/to are optional but recommended to keep responses bounded.
Default sort: start ascending.

Assumptions (explicit)

Time format
start and end are RFC 3339 / ISO 8601 timestamps (e.g., 2026-01-20T10:00:00Z).
end must be strictly greater than start.

Timezone
API stores and compares times in UTC.
Inputs must include an offset or Z. Responses are returned in UTC (Z).

Overlap definition (including back-to-back)
Treat bookings as half-open intervals: [start, end).
Two bookings overlap iff: new.start < existing.end AND existing.start < new.end.
Back-to-back is allowed: e.g., one ends at 11:00, another starts at 11:00 → no overlap.

Cancellation behavior
DELETE /bookings/{id} performs a soft cancel logically (status becomes canceled) but:
The minimal API returns 204 to keep it simple.
Canceled bookings are excluded by default from list results.
(If you need auditability, you’d add ?includeCanceled=true later.)

Booking ID
bookingId is server-generated, unique, opaque (string).
Clients must treat it as an immutable identifier and never derive meaning from it.
If you want the absolute-minimum version even further: drop title/createdBy and require only {start,end}—everything else is optional.

-------------------------------------------------------------------------------------------------------------------------------------
## 3. Toteutus: Säännöt ja ääritapaukset: 
-------------------------------------------------------------------------------------------------------------------------------------
### Prompti

Next, apply these rules exactly: bookings for the same room must not overlap, bookings cannot be in the past, start must be before end. Define overlap precisely (I want back-to-back bookings to be allowed). List the edge cases we must test, especially for overlap and time.

-------------------------------------------------------------------------------------------------------------------------------------
### AI-vastaus

Rules (applied exactly)
Assume all times are UTC RFC 3339 timestamps and comparisons use UTC instants.

1) Start/end validity
A booking request with start and end is valid only if:

Start must be before end: start < end
(start == end and start > end are invalid)

2) Not in the past
Let now be the server’s current UTC timestamp at validation time.

Bookings cannot be in the past: start >= now
(i.e., a booking whose start is earlier than “now” is rejected)

(This definition allows “start exactly at now”. If you don’t want that, change to start > now, but per your rule wording, >= is the strict reading.)

3) No overlap within the same room (back-to-back allowed)
For a given roomId, treat every booking as a half-open interval:

Booking interval is [start, end)
Two bookings A=[Astart, Aend) and B=[Bstart, Bend) overlap iff:

Astart < Bend AND Bstart < Aend
Equivalently, they do not overlap iff:

Aend <= Bstart OR Bend <= Astart
Back-to-back is allowed because:

If Aend == Bstart, then Astart < Bend is true but Bstart < Aend becomes Bstart < Bstart which is false → no overlap.

Edge cases to test (focus: overlap + time)

A) Start/end ordering
  start < end by 1 second (minimum non-zero duration you allow) → accept
  start == end → reject
  start > end → reject
  Very long duration (e.g., multi-day) → accept (unless you later add max duration)

B) “Not in the past” vs now
  Assume a fixed now in tests (freeze time), e.g. now = 2026-01-20T10:00:00Z.
  start = now - 1ns/1ms/1s (depending on precision) → reject
  start = now → accept
  start = now + 1s → accept
  end in the past but start not in the past is impossible if start < end; still worth a sanity test that your validator checks start vs now, not end.

  Precision edge: if you accept milliseconds, test boundary with millisecond precision; if seconds only, test second boundaries.

C) Overlap cases (existing booking E)
  Let existing booking E = [10:00, 11:00) in the same room.

Non-overlapping (should accept):
   Completely before: [09:00, 10:00) (end == E.start) → accept (back-to-back)
   Completely after: [11:00, 12:00) (start == E.end) → accept (back-to-back)
    Gap: [08:00, 09:30) → accept
    Gap after: [11:30, 12:00) → accept

Overlapping (should reject):
    Same interval: [10:00, 11:00) → reject
    Starts before, ends inside: [09:30, 10:30) → reject
    Starts inside, ends after: [10:30, 11:30) → reject
    Fully contained within: [10:15, 10:45) → reject
    Fully contains existing: [09:00, 12:00) → reject
    Touching start but not equal: [09:59:59, 10:00:01) → reject
    Touching end but not equal: [10:59:59, 11:00:01) → reject

Multiple existing bookings
Existing: [10:00,11:00) and [12:00,13:00)

New booking overlaps neither: [11:00,12:00) → accept
New booking overlaps first only: [10:30,11:30) → reject
New booking overlaps second only: [11:30,12:30) → reject
New booking bridges the gap and overlaps both ends: [10:30,12:30) → reject
New booking exactly covers the gap boundaries: [11:00,12:00) → accept

D) Cross-room behavior
  Same times as an existing booking but different roomId → accept (no overlap constraint across rooms)

E) Cancellation interaction (if canceled bookings are excluded from conflicts)
  Existing booking is canceled; new booking same interval → accept
  Cancel then immediately create back-to-back around it:
  Existing active [10:00,11:00); cancel it; create [10:00,11:00) → accept

F) Concurrency / race conditions (must test even with perfect overlap logic)
  Two clients simultaneously attempt to create [10:00,11:00) for the same room → exactly one succeeds, the other gets 409
  Two clients simultaneously attempt back-to-back that share boundaries with an existing booking:
  Existing [10:00,11:00), two creates: [09:00,10:00) and [11:00,12:00) → both succeed

G) Time parsing / normalization
  Inputs with timezone offsets that represent the same instant:
  2026-01-20T12:00:00+02:00 equals 2026-01-20T10:00:00Z
  Ensure comparisons happen after normalization → correct accept/reject
  Invalid timestamp formats → 400
  end far in future but start barely valid relative to now → validate correctly

If you want, I can also write these as a concrete test matrix (Given/When/Then) and include the exact expected HTTP status codes for each case.

-------------------------------------------------------------------------------------------------------------------------------------
## 4. Toteutus: FastAPI sekä koodin tuotto: 
-------------------------------------------------------------------------------------------------------------------------------------
### Prompti

Now implement the API using Python + FastAPI with an in-memory data store (no need to use MySQL or PostgreSQL). Keep it minimal and readable. The endpoints needed are: POST /bookings, DELETE /bookings/{booking_id}, GET /rooms/{room_id}/bookings. The input for create: {"room_id": "...", "start": "...", "end": "..."} using ISO-8601 timestamps WITH the timezone. Cancellation deletes the booking (hard delete). Enforce these rules: start must be before end, bookings cannot be in the past, and bookings for the same room must not overlap. Allow back-to-back by treating intervals as [start, end). 

Add status codes: 201 on create, 404 if cancelling unknow id, 409 on overlap conflict and 422 for validation errors (or explain clearly if you choose 400). Don't add extra features I didn't ask for. Output the full file contents and a simple folder structure.

-------------------------------------------------------------------------------------------------------------------------------------
### AI-vastaus

Folder structure:
meeting-room-api/
  main.py

main.py:
```python

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

```

Notes on status codes (as requested):

201 on create (set via decorator)
404 when deleting unknown booking id
409 on overlap conflict
422 for rule violations (start < end, start >= now, and timestamp must include timezone). FastAPI will also return 422 automatically for basic request-shape issues.

Run locally (example):

pip install fastapi uvicorn
uvicorn main:app --reload