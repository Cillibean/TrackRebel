import math
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from models import Event
from sqlalchemy import select, update, delete, insert


LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


def _parse_event_datetime(value):
    if not value:
        return None

    normalized = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    # Datetimes from DateTimeLocalField are naive; treat them as local time.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)

    return parsed.astimezone(timezone.utc)


def delete_expired_events(db):
    now_utc = datetime.now(timezone.utc)
    events = db.execute(select(Event)).scalars().all()

    expired_event_ids = []
    for event in events:
        end_time = _parse_event_datetime(event.end_time)
        if end_time and end_time <= now_utc:
            expired_event_ids.append(event.id)
            continue

        if not event.end_time:
            start_time = _parse_event_datetime(event.start_time)
            if start_time and start_time + timedelta(hours=24) <= now_utc:
                expired_event_ids.append(event.id)

    if expired_event_ids:
        db.execute(delete(Event).where(Event.id.in_(expired_event_ids)))
        db.commit()

    return len(expired_event_ids)

def add_event_to_db(submitted_event, event_id=None):
    with SessionLocal() as db:
        start_time_value = submitted_event["start_time"].isoformat() if submitted_event["start_time"] else None

        # If no start time is supplied on create, use creation time for 24-hour expiry.
        if start_time_value is None and event_id is None:
            start_time_value = datetime.now(timezone.utc).isoformat()

        event_values = {
            "title": submitted_event["name"],
            "description": submitted_event["description"] if submitted_event["description"] else "",
            "type": submitted_event["event_type"] if submitted_event["event_type"] else "",
            "category": submitted_event["category"] if submitted_event["category"] else "other",
            "link": submitted_event["link"] if submitted_event["link"] else None,
            "contact": submitted_event["contact"] if submitted_event["contact"] else None,
            "start_time": start_time_value,
            "end_time": submitted_event["end_time"].isoformat() if submitted_event["end_time"] else None,
            "latitude": float(submitted_event["latitude"]),
            "longitude": float(submitted_event["longitude"]),
            "submitter": submitted_event["submitter"],
        }

        existing_event = None
        if event_id is not None:
            existing_event = db.execute(select(Event).where(Event.id == event_id)).scalar_one_or_none()

        if existing_event:
            for key, value in event_values.items():
                setattr(existing_event, key, value)
            print(f"Event '{existing_event.title}' (id={existing_event.id}) updated by '{submitted_event['submitter']}'")
        else:
            event = Event(**event_values)
            db.add(event)
            print(f"Event '{event.title}' added to database by '{submitted_event['submitter']}'")

        db.commit()

def get_all_events(db):
    delete_expired_events(db)
    result = db.execute(select(Event)).scalars().all()
    list_of_events = []
    for event in result:
        list_of_events.append({
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "type": event.type,
            "category": event.category,
            "link": event.link,
            "contact": event.contact,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "submitter": event.submitter
        })
    return {"events": list_of_events}

def get_bounding_box(lat, lng, radius_km):
    lat = float(lat)
    lng = float(lng)
    radius_km = float(radius_km)
    lat_rad = math.radians(lat)
    
    delta_lat = radius_km / 111.1

    delta_lng = radius_km / (111.1 * math.cos(lat_rad))
    
    return {
        "min_lat": lat - delta_lat,
        "max_lat": lat + delta_lat,
        "min_lng": lng - delta_lng,
        "max_lng": lng + delta_lng
    }

def search_events(request):
    with SessionLocal() as db:
        delete_expired_events(db)
        bb = get_bounding_box(request.get("latitude"), request.get("longitude"), request.get("radius_km"))
        stmt = select(Event).filter(Event.title.ilike(f"%{request.get("name")}%") if request.get("name") else True,
                                        Event.submitter.ilike(f"%{request.get("submitter")}%") if request.get("submitter") else True,
                                        Event.start_time >= request.get("start_time") if request.get("start_time") else True,
                                        Event.end_time <= request.get("end_time") if request.get("end_time") else True,
                                        Event.latitude >= bb["min_lat"],
                                        Event.latitude <= bb["max_lat"],
                                        Event.longitude >= bb["min_lng"],
                                        Event.longitude <= bb["max_lng"],
                                        Event.category == request.get("category") if request.get("category") and request.get("category") != "all" else True,
                                        Event.type == request.get("event_type") if request.get("event_type") and request.get("event_type") != "all" else True)
        result=db.execute(stmt).scalars().all()
        print(f"Search returned {len(result)} event(s) for query: {request}")
        list_of_events = []
        for event in result:
            list_of_events.append({
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "type": event.type,
                "category": event.category,
                "link": event.link,
                "contact": event.contact,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "submitter": event.submitter
            })
        return {"events": list_of_events}
    
def get_event_by_id(event_id):
    with SessionLocal() as db:
        delete_expired_events(db)
        stmt = select(Event).filter(Event.id == event_id)
        result = db.execute(stmt).scalar_one_or_none()
        if result:
            return {
                "id": result.id,
                "title": result.title,
                "description": result.description,
                "type": result.type,
                "category": result.category,
                "link": result.link,
                "contact": result.contact,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "latitude": result.latitude,
                "longitude": result.longitude,
                "submitter": result.submitter
            }
        else:
            return None

def update_event_in_db(event_id, updated_event):
    with SessionLocal() as db:
        stmt = update(Event).where(Event.id == event_id).values(
            title=updated_event["name"],
            description=updated_event["description"] if updated_event["description"] else "",
            type=updated_event["event_type"] if updated_event["event_type"] else "",
            category=updated_event["category"] if updated_event["category"] else "other",
            link=updated_event["link"] if updated_event["link"] else None,
            contact=updated_event["contact"] if updated_event["contact"] else None,
            start_time=updated_event["start_time"].isoformat() if updated_event["start_time"] else None,
            end_time=updated_event["end_time"].isoformat() if updated_event["end_time"] else None,
            latitude=float(updated_event["latitude"]),
            longitude=float(updated_event["longitude"])
        )
        db.execute(stmt)
        db.commit()
        print(f"Event with id {event_id} updated successfully")


def delete_event_by_id(event_id):
    with SessionLocal() as db:
        stmt = delete(Event).where(Event.id == event_id)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount