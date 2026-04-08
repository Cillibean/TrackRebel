import os
from database import SessionLocal, engine, Base
from models import User

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

        seed_user(db, "test", "test", "Test")

if __name__ == "__main__":
    seed_admin()