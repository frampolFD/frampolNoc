from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, UserRole


def _dev_bypass_user(db: Session) -> User | None:
    """FRAMPOL_SKIP_AUTH dev/demo convenience: auto-authenticate as the
    seeded admin instead of requiring a login. Off by default (see
    app/config.py); only meant for local iteration before auth work is
    prioritized."""
    if not settings.skip_auth:
        return None
    return db.query(User).filter(User.role == UserRole.admin).first() or db.query(User).first()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    bypass_user = _dev_bypass_user(db)
    if bypass_user:
        return bypass_user

    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    bypass_user = _dev_bypass_user(db)
    if bypass_user:
        return bypass_user

    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)
