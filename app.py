from flask import Flask, request, jsonify
from database import SessionLocal
from sqlalchemy import select, update, delete, insert
from models import User
from contextlib import contextmanager

from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
import os

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-secret")

jwt = JWTManager(app)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/login")
def post_login():
    data = request.json

    with get_db() as db:
        stmt = select(User).where(User.username == data["username"]).limit(1)
        user = db.execute(stmt).scalar_one_or_none()

        if user and user.check_password(data["password"]):
            token = create_access_token(identity=user.id)
            return {"access_token": token}

    return {"error": "bad credentials"}, 401

@app.get("/protected")
@jwt_required()
def protected():
    user_id = get_jwt_identity()
    return {"logged_in_as": user_id}

@app.get("/")
def index():
    return "Hello, World!" 

if __name__ == "__main__":
    app.run(debug=True)