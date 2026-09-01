"""One-time seed data: the admin user and a starter ISP list.

Run with: python -m app.seed
Safe to re-run — it only creates records that don't already exist.
"""
from app.config import settings
from app.database import SessionLocal
from app.models import ISP, User, UserRole
from app.security import hash_password

STARTER_ISPS = [
    ("Liquid", "liquid"),
    ("TelOne", "telone"),
    ("Dandemutande", "dandemutande"),
    ("Starlink", "starlink"),
    ("ZOL", "zol"),
    ("Other", "other"),
]


def run():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == settings.admin_email).first():
            db.add(
                User(
                    name="Admin",
                    email=settings.admin_email,
                    role=UserRole.admin,
                    password_hash=hash_password(settings.admin_password),
                )
            )
            print(f"Created admin user: {settings.admin_email}")
        else:
            print(f"Admin user already exists: {settings.admin_email}")

        for name, badge_key in STARTER_ISPS:
            if not db.query(ISP).filter(ISP.name == name).first():
                db.add(ISP(name=name, badge_key=badge_key))
                print(f"Created ISP: {name}")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
