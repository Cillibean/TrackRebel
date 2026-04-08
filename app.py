from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update, delete, insert
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from forms import LoginForm
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
import os

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

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = None
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif request.cookies.get("access_token"):
        cookie_value = request.cookies.get("access_token")
        if cookie_value.startswith("Bearer "):
            token = cookie_value.split(" ", 1)[1]
        else:
            token = cookie_value

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

@app.get("/login")
async def login_form(request: Request):
    form = LoginForm()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "form": form, "error": None, "success": None},
    )

@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = LoginForm(formdata=await request.form())
    error = None
    success = None
    token = None

    if form.validate():
        user = db.execute(select(User).filter(User.username == form.username.data)).scalar_one_or_none()
        if user and user.check_password(form.password.data):
            token = create_access_token(data={"sub": str(user.id)})
            success = "Login successful. Token issued and stored in cookie."
        else:
            error = "Incorrect username or password"
    else:
        error = "Please fix the highlighted fields and try again."

    response = templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "form": form,
            "error": error,
            "success": success,
            "token": token,
        },
    )

    if token:
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            secure=True,
            samesite="lax",
        )

    return response

@app.get("/protected")
async def protected(current_user: User = Depends(get_current_user)):
    return {"logged_in_as": current_user.id}

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)