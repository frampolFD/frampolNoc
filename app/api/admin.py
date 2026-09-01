from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, UserRole
from app.schemas import SystemSettingsOut, SystemSettingsUpdate
from app.settings_store import get_or_create_settings

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_current_user)])


def _require_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.get("/settings", response_model=SystemSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return get_or_create_settings(db)


@router.put("/settings", response_model=SystemSettingsOut)
def update_settings(payload: SystemSettingsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_admin(user)
    row = get_or_create_settings(db)
    row.icmp_interval_seconds = payload.icmp_interval_seconds
    row.snmp_interval_seconds = payload.snmp_interval_seconds
    db.commit()
    db.refresh(row)
    return row
