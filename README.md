# Kokoushuoneiden Varausrajapinta

Yksinkertainen FastAPI-pohjainen rajapinta kokoushuoneiden varausten hallintaan. Tukee varausten luontia, peruuttamista ja listaamista.

## Ominaisuudet
- Varauksen luonti, peruutus ja listaaminen huonekohtaisesti.
- Ei päällekkäisiä varauksia, ei menneisyysvarauksia.

## Asennus
1. Asenna riippuvuudet: `pip install fastapi uvicorn pydantic pytest`

## Käynnistäminen
```
uvicorn main:app --reload
```
Sovellus käynnistyy: `http://127.0.0.1:8000`

## API-dokumentaatio
Avaa: `http://127.0.0.1:8000/docs` (Swagger UI).

## API-esimerkit

### Varauksen luonti (POST /bookings)
```json
{
  "room_id": "huone1",
  "start": "2030-01-01T10:00:00Z",
  "end": "2030-01-01T11:00:00Z"
}
```

### Varauksen peruutus (DELETE /bookings/{id})

### Huoneen varaukset (GET /rooms/{room_id}/bookings)

## Testaus
```
pytest
```

## Tiedostorakenne
- `api.py`: Rajapinnat
- `main.py`: Sovelluksen aloitus
- `models.py`: Mallit
- `repository.py`: Tietovarasto
- `services.py`: Logiikka
- `tests/`: Testit