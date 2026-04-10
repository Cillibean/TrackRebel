# TrackRebel

TrackRebel is a protest tracker application designed as a base platform for Irish republicans and rebels to coordinate resistance activity, events, and organizing.

## Vision 🎯

Track actions, coordinate events, and support local organizing through a map-first web interface.

## Credits And Attribution 👥

- **Primary author and code owner:** Cillian O Riain 👨‍💻
- This codebase builds on human-written architecture and patterns from Cillian O Riain's previous projects.
- AI assistance was used for interface styling, layout refinement, and parts of site scaffolding.

## Current Features ✨

- FastAPI backend with Jinja templates 🚀
- JWT-based authentication using HTTP-only cookies 🔐
- Register, login, logout flows
- Home page map with all active (non-expired) events
- Add Event flow with map-based coordinate selection
- Edit and delete permissions scoped to event submitter
- Event details page (`/events/info/{event_id}`)
- Search page with map-centered location filtering
- Radius search (`1-200km`) using map center coordinates
- Category and type filtering via chip-based UI
- Name/title keyword filtering
- Time-window search support (`start_time` / `end_time` inputs)
- Time overlap logic in search so valid ongoing/relevant events are not incorrectly excluded
- Support for events with missing `start_time`, missing `end_time`, or both during search filtering
- Background cleanup of expired events at startup and on interval
- WTForms validation for add/search/auth forms
- Static asset linking via `request.url_for('static', path=...)` for deployment compatibility

## Search Behavior 🔎

- Search is centered on the current map center and constrained by selected radius.
- Category/type defaults are `all` (no category/type exclusion).
- Date fields are optional; if provided, search uses overlap behavior:
     events are returned when their effective event window overlaps the search window.
- If an event has only one time bound:
     the missing bound is treated as the same instant for overlap checks.
- If an event has no parseable time bounds:
     it is not excluded purely by time filters.

## Routes Overview 🧭

- `GET /`: home map view
- `GET /login`, `POST /login`: authentication
- `GET /register`, `POST /register`: account creation
- `GET /logout`: clear auth cookie
- `GET /events/search`, `POST /events/search`: search map and filters
- `GET /events/add`, `POST /events/add`: create event (authenticated)
- `GET /events/edit/{event_id}`, `POST /events/edit/{event_id}`: update event (owner only)
- `GET /events/info/{event_id}`: event details
- `POST /events/delete/{event_id}`: delete event (owner only)

## Stack 🧰

- Python
- FastAPI
- SQLAlchemy
- WTForms
- Jinja2
- Leaflet.js
- SQLite (local development)
- PostgreSQL (Render deployment)

## Run Locally 💻

1. Install dependencies:

     ```bash
     python -m pip install -r requirements.txt
     ```

2. Start the app:

     ```bash
     uvicorn app:app --reload
     ```

3. Open:
     `http://127.0.0.1:8000/`

4. Optional: seed admin user:

     ```bash
     python seed.py
     ```

5. Optional: seed fake test events (local debugging only):

     ```bash
     python seed.py --fake-events 20 --reset-fake-events
     ```

6. Optional: seed time edge-case events (missing start/end times):

     ```bash
     python seed.py --edge-time-events
     ```

7. Optional: remove previously seeded fake/edge test events:

     ```bash
     # Example using Python snippet from project root
     python -c "from database import SessionLocal; from models import Event; db=SessionLocal(); db.query(Event).filter(Event.submitter.in_(['seed_bot','seed_bot_edge'])).delete(synchronize_session=False); db.commit(); db.close()"
     ```

## Seeding Reference 🌱

- `python seed.py`
     Seeds admin user only (requires `ADMIN_USERNAME` and `ADMIN_PASSWORD`).
- `python seed.py --fake-events N --reset-fake-events`
     Seeds N synthetic events for manual map/search testing and optionally clears existing fake events first.
- `python seed.py --edge-time-events`
     Seeds edge-case events with missing start/end time combinations for search testing.

## Environment Variables 🔧

### Local (`.env`) 🏠

- `LOCAL_DATABASE_URL`
- `JWT_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

### Render ☁️

- `DATABASE_URL` (PostgreSQL)
- `JWT_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

## Deployment Notes 🚢

- Use Uvicorn as the web process on Render.
- Keep static resources referenced via `request.url_for('static', path=...)` to avoid path issues in deployment.
- Running `python seed.py` with no flags only seeds admin credentials (when env vars are present).
- Fake and edge-case events are only created when explicit flags are passed (`--fake-events`, `--edge-time-events`).
- Local seeding only affects whichever database URL the running environment is pointed at.

## Disclaimer ⚠️

This software is provided as a base coordination tool. Users are responsible for operating within applicable laws, platform terms, and community safety standards.
