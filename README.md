# Bookify API

A minimal Django REST Framework backend for managing events and bookings.

## Features

- Custom user model using `accounts.User`
- Event model with list and retrieve endpoints
- Booking model with authenticated create and list endpoints
- Validation to prevent a user from booking the same event twice

## Tech Stack

- Python
- Django
- Django REST Framework
- SQLite (default for local development)

## Project Structure

```text
accounts/
bookings/
config/
events/
tests/
manage.py
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Apply migrations:

```bash
python manage.py migrate
```

4. Create a superuser if needed:

```bash
python manage.py createsuperuser
```

5. Start the development server:

```bash
python manage.py runserver
```

6. Start Redis. The default URL used by both Django cache and Celery is `redis://127.0.0.1:6379/1`.

7. Start the Celery worker:

```bash
celery -A config worker --loglevel=info
```

## Run Tests

```bash
pytest
```

## API Endpoints

Base path: `/api/`

- `GET /api/schema/` - OpenAPI schema
- `GET /api/docs/` - Swagger UI
- `GET /api/redoc/` - ReDoc
- `POST /api/token/` - Obtain JWT access and refresh tokens
- `POST /api/token/refresh/` - Refresh a JWT access token
- `GET /api/events/` - List events
- `GET /api/events/<id>/` - Retrieve a single event
- `POST /api/bookings/` - Create a booking for the authenticated user
- `GET /api/bookings/` - List the authenticated user's bookings
- `GET /api/bookings/<id>/` - Retrieve a single booking owned by the authenticated user

## Booking Rules

- A user cannot book the same event more than once.
- Booking endpoints require JWT authentication.

## Authentication

Use the token endpoint to obtain JWT credentials:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"your-username\", \"password\": \"your-password\"}"
```

Then send the access token in the `Authorization` header:

```text
Authorization: Bearer <access_token>
```

## Notes

- The default database is SQLite for local development.
- Update `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` before deploying.
- The custom user model is configured as `accounts.User`.
- Booking payment processing and email confirmations are queued asynchronously through Celery.
- Interactive API documentation is available at `/api/docs/` and `/api/redoc/`.
