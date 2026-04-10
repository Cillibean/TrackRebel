import os
import argparse
from datetime import datetime, timedelta, timezone

from database import SessionLocal, engine, Base
from models import User, Event

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


def seed_user(db, username: str, password: str, label: str):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        print(f"{label} user '{username}' already exists")
        return

    user = User(username=username)
    user.set_password(password)
    db.add(user)
    db.commit()
    print(f"{label} user '{username}' created successfully")


def seed_admin():
    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    with SessionLocal() as db:
        if admin_username and admin_password:
            seed_user(db, admin_username, admin_password, "Admin")
        else:
            print("Skipping admin seed: set ADMIN_USERNAME and ADMIN_PASSWORD to create an admin user")


def _build_fake_events(count: int):
    now = datetime.now(timezone.utc)
    templates = [
        ("Dublin", 53.3498, -6.2603, "protest", "political"),
        ("Cork", 51.8985, -8.4756, "meeting", "social"),
        ("Galway", 53.2707, -9.0568, "march", "cost_of_living"),
        ("Limerick", 52.6638, -8.6267, "community_support", "housing"),
        ("Belfast", 54.5973, -5.9301, "incident_report", "other"),
        ("Waterford", 52.2593, -7.1101, "protest", "environmental"),
        ("Sligo", 54.2766, -8.4761, "meeting", "economic"),
        ("Kilkenny", 52.6541, -7.2448, "march", "fuel"),
        ("Derry", 55.0068, -7.3183, "protest", "international"),
        ("Athlone", 53.4239, -7.9407, "community_support", "social"),
    ]

    events = []
    for i in range(count):
        city, lat, lng, event_type, category = templates[i % len(templates)]
        starts_at = now + timedelta(days=(i % 14), hours=(i % 6))
        ends_at = starts_at + timedelta(hours=2 + (i % 4))
        events.append(
            {
                "title": f"[SEED] Test Event {i + 1:02d} - {city}",
                "description": f"Synthetic test event #{i + 1} generated for map/search debugging.",
                "type": event_type,
                "category": category,
                "start_time": starts_at.isoformat(),
                "end_time": ends_at.isoformat(),
                "latitude": lat,
                "longitude": lng,
                "submitter": "seed_bot",
                "link": "https://example.org/event",
                "contact": "seed@example.org",
            }
        )
    return events


def seed_fake_events(count: int, reset_existing: bool = False):
    fake_events = _build_fake_events(count)

    with SessionLocal() as db:
        if reset_existing:
            deleted = db.query(Event).filter(Event.submitter == "seed_bot").delete()
            db.commit()
            print(f"Deleted {deleted} existing fake event(s)")

        created = 0
        skipped = 0
        for item in fake_events:
            exists = (
                db.query(Event)
                .filter(Event.title == item["title"], Event.submitter == item["submitter"])
                .first()
            )
            if exists:
                skipped += 1
                continue

            db.add(Event(**item))
            created += 1

        db.commit()
        print(f"Fake events seeded: created={created}, skipped={skipped}")


def seed_time_edge_case_events():
    now = datetime.now(timezone.utc)
    edge_events = [
        {
            "title": "[SEED-EDGE] No End Time - Dublin",
            "description": "Edge-case event with start_time only.",
            "type": "protest",
            "category": "political",
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": None,
            "latitude": 53.3498,
            "longitude": -6.2603,
            "submitter": "seed_bot_edge",
            "link": "https://example.org/edge-start-only",
            "contact": "edge@example.org",
        },
        {
            "title": "[SEED-EDGE] No Start Time - Cork",
            "description": "Edge-case event with end_time only.",
            "type": "meeting",
            "category": "social",
            "start_time": None,
            "end_time": (now + timedelta(days=2, hours=3)).isoformat(),
            "latitude": 51.8985,
            "longitude": -8.4756,
            "submitter": "seed_bot_edge",
            "link": "https://example.org/edge-end-only",
            "contact": "edge@example.org",
        },
        {
            "title": "[SEED-EDGE] No Start Or End - Galway",
            "description": "Edge-case event with no time fields.",
            "type": "march",
            "category": "cost_of_living",
            "start_time": None,
            "end_time": None,
            "latitude": 53.2707,
            "longitude": -9.0568,
            "submitter": "seed_bot_edge",
            "link": "https://example.org/edge-no-times",
            "contact": "edge@example.org",
        },
        {
            "title": "[SEED-EDGE] No End Time - Belfast",
            "description": "Second start-only edge-case event.",
            "type": "community_support",
            "category": "other",
            "start_time": (now + timedelta(days=4, hours=2)).isoformat(),
            "end_time": None,
            "latitude": 54.5973,
            "longitude": -5.9301,
            "submitter": "seed_bot_edge",
            "link": "https://example.org/edge-start-only-2",
            "contact": "edge@example.org",
        },
    ]

    with SessionLocal() as db:
        created = 0
        skipped = 0
        for item in edge_events:
            exists = (
                db.query(Event)
                .filter(Event.title == item["title"], Event.submitter == item["submitter"])
                .first()
            )
            if exists:
                skipped += 1
                continue

            db.add(Event(**item))
            created += 1

        db.commit()
        print(f"Edge-case events seeded: created={created}, skipped={skipped}")


def parse_args():
    parser = argparse.ArgumentParser(description="Seed users and optional fake events")
    parser.add_argument(
        "--fake-events",
        type=int,
        default=0,
        help="Number of fake events to seed for testing",
    )
    parser.add_argument(
        "--reset-fake-events",
        action="store_true",
        help="Delete existing fake events (submitter=seed_bot) before seeding",
    )
    parser.add_argument(
        "--edge-time-events",
        action="store_true",
        help="Seed events with missing start/end times for search edge-case testing",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seed_admin()
    if args.fake_events > 0:
        seed_fake_events(args.fake_events, reset_existing=args.reset_fake_events)
    if args.edge_time_events:
        seed_time_edge_case_events()