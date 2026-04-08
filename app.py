from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update, delete, insert
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from forms import LoginForm, AddEventForm
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
            token = create_access_token(data={"sub": str(user.username)})
    
    response =  templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"form": form}
    )
    
    if token:
        user = form.username.data
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            secure=True,
            samesite="lax",
        )

    return response

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get("/")
async def index(request: Request, current_user: Optional[User] = Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=base_context(request, current_user)
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
        },
    )


@app.post("/events/add")
async def add_event_submit(request: Request, current_user: User = Depends(get_current_user)):
    form = AddEventForm(formdata=await request.form())
    error = None
    success = None
    submitted_event = None

    if form.validate():
        success = "Event draft captured. You can wire this to your database model next."
        submitted_event = {
            "name": form.name.data,
            "description": form.description.data,
            "start_time": form.start_time.data,
            "end_time": form.end_time.data,
            "event_type": form.event_type.data,
            "latitude": form.latitude.data,
            "longitude": form.longitude.data,
            "submitter": current_user.username
        }
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
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)