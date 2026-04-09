import logging
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update, delete, insert
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from events_db import add_event_to_db, get_all_events, get_event_by_id, delete_expired_events, delete_event_by_id, search_events
from models import User
from forms import LoginForm, AddEventForm, RegistrationForm, SearchForm, Category, Type
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import Optional
import os

# Use uvicorn's error logger so stack traces appear in the uvicorn terminal.
logger = logging.getLogger("uvicorn.error")

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
CLEANUP_INTERVAL_SECONDS = 300
cleanup_task: Optional[asyncio.Task] = None


@app.middleware("http")
async def log_unhandled_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled exception for %s %s", request.method, request.url.path)
        raise


@app.on_event("startup")
async def startup_init_db():
    global cleanup_task
    if SECRET_KEY == "dev-secret":
        logger.warning(
            "JWT_SECRET_KEY is not set — using insecure default. "
            "Set the JWT_SECRET_KEY environment variable before deploying."
        )
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified at startup")
    cleanup_task = asyncio.create_task(_expired_events_cleanup_loop())


@app.on_event("shutdown")
async def shutdown_cleanup_worker():
    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        cleanup_task = None


async def _expired_events_cleanup_loop():
    while True:
        try:
            with SessionLocal() as db:
                deleted_count = delete_expired_events(db)
                if deleted_count:
                    logger.info("Deleted %s expired event(s)", deleted_count)
        except Exception:
            logger.exception("Background event cleanup failed")

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _read_token(request: Request) -> Optional[str]:
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1]

    cookie_value = request.cookies.get("access_token")
    if cookie_value:
        return cookie_value.split(" ", 1)[1] if cookie_value.startswith("Bearer ") else cookie_value

    return None

def _get_user_from_token(token: str, db: Session) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = _read_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _get_user_from_token(token, db)

async def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = _read_token(request)
    if not token:
        request.state.authenticated = False
        request.state.auth_error = "no_token"
        return None

    try:
        user = _get_user_from_token(token, db)
        request.state.authenticated = True
        request.state.auth_error = None
        return user
    except HTTPException as exc:
        request.state.authenticated = False
        request.state.auth_error = exc.detail
        return None
    
def base_context(request: Request, current_user: Optional[User] = Depends(get_current_user_optional)):
    return {
        "user": current_user,
        "logged_in": current_user is not None,
        "authenticated": getattr(request.state, "authenticated", False),
        "auth_error": getattr(request.state, "auth_error", None),
    }


def _build_filter_options(enum_cls, emoji_map: dict[str, str], note_map: dict[str, str], all_label: str, all_emoji: str, all_note: str):
    options = [
        {
            "value": "all",
            "label": all_label,
            "emoji": all_emoji,
            "note": all_note,
        }
    ]

    for item in enum_cls:
        options.append(
            {
                "value": item.value,
                "label": item.value.replace("_", " ").title(),
                "emoji": emoji_map.get(item.value, "🧭"),
                "note": note_map.get(item.value, "Mapped filter option."),
            }
        )

    return options


SEARCH_CATEGORY_OPTIONS = _build_filter_options(
    Category,
    {
        "fuel": "⛽",
        "cost_of_living": "🛒",
        "housing": "🏠",
        "international": "🌍",
        "palestine": "🇵🇸",
        "social": "🤝",
        "environmental": "🌿",
        "economic": "📈",
        "republican": "☘️",
        "anti_government": "🏴",
        "political": "🏛️",
        "other": "🧭",
    },
    {
        "fuel": "Fuel costs, supply pressure, and energy action",
        "cost_of_living": "Bills, prices, and household pressure",
        "housing": "Rents, evictions, and tenant action",
        "international": "International solidarity and global response",
        "palestine": "Solidarity actions and demonstrations",
        "social": "Community issues and solidarity work",
        "environmental": "Climate, land, water, and local impact",
        "economic": "Jobs, austerity, and wider economic pressure",
        "republican": "Republican events, memorials, and mobilisation",
        "anti_government": "Direct opposition to government policy",
        "political": "Campaigns, policy, and public response",
        "other": "Anything outside the main category set",
    },
    "All Categories",
    "🗂️",
    "Show every category on the map",
)


SEARCH_TYPE_OPTIONS = _build_filter_options(
    Type,
    {
        "protest": "📢",
        "meeting": "🗣️",
        "march": "🚶",
        "community_support": "🧰",
        "incident_report": "⚠️",
        "other": "🧭",
    },
    {
        "protest": "Direct demonstration and turnout",
        "meeting": "Assemblies, briefings, and planning sessions",
        "march": "Route-based public mobilisation",
        "community_support": "Mutual aid and local support efforts",
        "incident_report": "Reports tied to a place on the map",
        "other": "Catch-all for anything outside the main set",
    },
    "All Types",
    "🧩",
    "Show every event type on the map",
)

@app.get("/login")
async def login_form(request: Request):
    form = LoginForm()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "form": form},
    )

@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = LoginForm(formdata=await request.form())
    token = None
    user = None

    if form.validate():
        user = db.execute(select(User).filter(User.username == form.username.data)).scalar_one_or_none()
        if user and user.check_password(form.password.data):
            logger.info(f"User {form.username.data} logged in successfully")
            token = create_access_token(data={"sub": str(user.username)})
    
    response =  templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"form": form}
    )
    
    if token:
        user = form.username.data
        response = RedirectResponse(url="/", status_code=302)
        use_secure_cookie = request.url.scheme == "https"
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            secure=use_secure_cookie,
            samesite="lax",
        )

    logger.info(f"Login attempt for user {form.username.data}, success: {token is not None}")
    return response

@app.get("/register")
async def register_form(request: Request):
    form = RegistrationForm()
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "form": form},
    )

@app.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    form = RegistrationForm(formdata=await request.form())
    error = None
    
    if form.validate():
        existing_user = db.execute(select(User).filter(User.username == form.username.data)).scalar_one_or_none()
        if existing_user:
            error = "Username already exists. Please choose another."
        else:
            new_user = User(
                username=form.username.data,
                email=form.email.data if form.email.data else None,
                phone=form.phone.data if form.phone.data else None
            )
            new_user.set_password(form.password.data)
            db.add(new_user)
            db.commit()
            logger.info(f"New user registered: {form.username.data}")
            return RedirectResponse(url="/login", status_code=302)
    else:
        error = "Registration failed. Please check your inputs."
    
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "form": form, "error": error},
    )

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get("/")
async def index(request: Request, current_user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    all_events = get_all_events(db)
    all_events = all_events.get("events", []) if all_events else []
    logger.info(f"Fetched all events: {all_events}")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            **base_context(request, current_user),
            "all_events": all_events
        }
    )


@app.get("/events/search")
async def search_page(request: Request, current_user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    all_events = []
    search_form = SearchForm(data={"category": "all", "event_type": "all", "radius_km": 25})
    logger.info("Loaded search page with %s event(s)", len(all_events))

    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={
            **base_context(request, current_user),
            "all_events": all_events,
            "category_options": SEARCH_CATEGORY_OPTIONS,
            "search_form": search_form,
            "type_options": SEARCH_TYPE_OPTIONS,
            "shell_class": "shell-wide",
        },
    )

@app.post("/events/search")
async def search_submit(request: Request, current_user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    form = SearchForm(formdata=await request.form())
    search_results = []
    if form.validate():
        search_criteria = {
            "name": form.name.data,
            "latitude": form.latitude.data,
            "longitude": form.longitude.data,
            "category": form.category.data,
            "event_type": form.event_type.data,
            "start_time": form.start_time.data.isoformat() if form.start_time.data else None,
            "end_time": form.end_time.data.isoformat() if form.end_time.data else None,
            "radius_km": form.radius_km.data or 25,
        }
        logger.info(f"Performing search with criteria: {search_criteria}")
        search_results = search_events(search_criteria)
        logger.info(f"Search returned {len(search_results.get('events', []))} event(s)")
    else:
        logger.info(f"Search form validation failed: {form.errors}")

    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={
            **base_context(request, current_user),
            "all_events": search_results.get("events", []),
            "category_options": SEARCH_CATEGORY_OPTIONS,
            "search_form": form,
            "type_options": SEARCH_TYPE_OPTIONS,
            "shell_class": "shell-wide",
        },
    )

@app.get("/events/add")
async def add_event_form(request: Request, current_user: User = Depends(get_current_user)):
    form = AddEventForm()
    return templates.TemplateResponse(
        request=request,
        name="add_event.html",
        context={
            **base_context(request, current_user),
            "form": form,
            "error": None,
            "success": None,
            "submitted_event": None,
            "form_title": "Add Event",
            "form_intro": "Select the event location directly on the map, then complete the event details in the form.",
            "submit_label": "Add Event",
        },
    )

@app.post("/events/add")
async def add_event_submit(request: Request, current_user: User = Depends(get_current_user)):
    form = AddEventForm(formdata=await request.form())
    error = None
    success = None
    submitted_event = None

    if form.validate():
        success = "Event saved successfully."
        submitted_event = {
            "name": form.name.data,
            "description": form.description.data,
            "link": form.link.data,
            "contact": form.contact.data,
            "start_time": form.start_time.data,
            "end_time": form.end_time.data,
            "event_type": form.event_type.data,
            "category": form.category.data,
            "latitude": form.latitude.data,
            "longitude": form.longitude.data,
            "submitter": current_user.username
        }

        try:
            add_event_to_db(submitted_event)
        except Exception:
            logger.exception("Failed to add event to database")
            error = "Unable to save event right now. Please try again."
            success = None
    else:
        error = "Please complete all required fields and pick a location on the map."

    logger.info(f"Form validation result: {form.errors}, submitted_event: {submitted_event}, error: {error}, success: {success}")

    return templates.TemplateResponse(
        request=request,
        name="add_event.html",
        context={
            **base_context(request, current_user),
            "form": form,
            "error": error,
            "success": success,
            "submitted_event": submitted_event,
            "form_title": "Add Event",
            "form_intro": "Select the event location directly on the map, then complete the event details in the form.",
            "submit_label": "Add Event",
        },
    )


def _parse_event_datetime(value: Optional[str]):
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _format_event_datetime(value: Optional[str]) -> Optional[str]:
    parsed = _parse_event_datetime(value)
    if not parsed:
        return None

    # Render as concise local date/time without timezone suffix.
    local_dt = parsed.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M")


@app.get("/events/edit/{event_id}")
async def edit_event_form(request: Request, event_id: int, current_user: User = Depends(get_current_user)):
    event = get_event_by_id(event_id)
    logger.info(f"Fetched event for editing with id {event_id}: {event}")
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.get("submitter") != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to edit this event")

    form = AddEventForm(
        data={
            "name": event.get("title", ""),
            "description": event.get("description", ""),
            "link": event.get("link", ""),
            "contact": event.get("contact", ""),
            "start_time": _parse_event_datetime(event.get("start_time")),
            "end_time": _parse_event_datetime(event.get("end_time")),
            "event_type": event.get("type", "other"),
            "category": event.get("category", "other"),
            "latitude": str(event.get("latitude", "")),
            "longitude": str(event.get("longitude", "")),
        }
    )


    return templates.TemplateResponse(
        request=request,
        name="add_event.html",
        context={
            **base_context(request, current_user),
            "form": form,
            "error": None,
            "success": None,
            "submitted_event": None,
            "form_title": "Edit Event",
            "form_intro": "Update the event details and click Save Event to apply your changes.",
            "submit_label": "Save Event",
        },
    )


@app.post("/events/edit/{event_id}")
async def edit_event_submit(request: Request, event_id: int, current_user: User = Depends(get_current_user)):
    existing_event = get_event_by_id(event_id)
    if not existing_event:
        raise HTTPException(status_code=404, detail="Event not found")
    if existing_event.get("submitter") != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to edit this event")

    form = AddEventForm(formdata=await request.form())
    error = None
    success = None
    submitted_event = None

    if form.validate():
        submitted_event = {
            "name": form.name.data,
            "description": form.description.data,
            "link": form.link.data,
            "contact": form.contact.data,
            "start_time": form.start_time.data,
            "end_time": form.end_time.data,
            "event_type": form.event_type.data,
            "category": form.category.data,
            "latitude": form.latitude.data,
            "longitude": form.longitude.data,
            "submitter": current_user.username,
        }

        try:
            add_event_to_db(submitted_event, event_id=event_id)
            return RedirectResponse(url=f"/events/info/{event_id}", status_code=302)
        except Exception:
            logger.exception("Failed to update event %s", event_id)
            error = "Unable to save changes right now. Please try again."
    else:
        error = "Please complete all required fields and pick a location on the map."

    return templates.TemplateResponse(
        request=request,
        name="add_event.html",
        context={
            **base_context(request, current_user),
            "form": form,
            "error": error,
            "success": success,
            "submitted_event": submitted_event,
            "form_title": "Edit Event",
            "form_intro": "Update the event details and click Save Event to apply your changes.",
            "submit_label": "Save Event",
        },
    )

@app.get("/events/info/{event_id}")
async def event_info(request: Request, event_id: int, current_user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    event = get_event_by_id(event_id)
    logger.info(f"Fetched event for id {event_id}: {event}")
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event["start_time_display"] = _format_event_datetime(event.get("start_time"))
    event["end_time_display"] = _format_event_datetime(event.get("end_time"))
    events = [event]

    return templates.TemplateResponse(
        request=request,
        name="event_info.html",
        context={
            **base_context(request, current_user),
            "events": events
        }
    )


@app.post("/events/delete/{event_id}")
async def delete_event_submit(request: Request, event_id: int, current_user: User = Depends(get_current_user)):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.get("submitter") != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to delete this event")

    try:
        deleted_rows = delete_event_by_id(event_id)
        if not deleted_rows:
            raise HTTPException(status_code=404, detail="Event not found")
        logger.info("Event %s deleted by %s", event_id, current_user.username)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete event %s", event_id)
        raise HTTPException(status_code=500, detail="Unable to delete event right now. Please try again.")

    return RedirectResponse(url="/", status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)