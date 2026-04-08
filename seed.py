import os
from database import SessionLocal, engine, Base
from models import User

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def seed_admin():
    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_username or not admin_password:
        print("ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set")
        return

    with SessionLocal() as db:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == admin_username).first()
        if existing_admin:
            print(f"Admin user '{admin_username}' already exists")
            return

        # Create admin user
        admin = User(username=admin_username)
        admin.set_password(admin_password)
        db.add(admin)
        db.commit()
        print(f"Admin user '{admin_username}' created successfully")

if __name__ == "__main__":
    seed_admin()