from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.health import compute_health
from app.models import Alert, Customer, MonitoringStatus, WANLink
from app.schemas import AlertOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("")
def dashboard_summary(db: Session = Depends(get_db)):
    total_customers = db.query(Customer).count()
    wan_links = db.query(WANLink).all()

    online = offline = warning = disabled = 0
    for w in wan_links:
        if w.monitoring_status == MonitoringStatus.not_configured:
            disabled += 1
            continue
        health = compute_health(db, w)
        if health == "critical":
            offline += 1
        elif health == "warning":
            warning += 1
        elif health == "healthy":
            online += 1
        else:
            disabled += 1

    recent_alerts = db.query(Alert).order_by(Alert.started_at.desc()).limit(10).all()

    return {
        "total_customers": total_customers,
        "total_wan_links": len(wan_links),
        "online": online,
        "offline": offline,
        "warning": warning,
        "monitoring_disabled": disabled,
        "recent_alerts": [AlertOut.model_validate(a).model_dump(mode="json") for a in recent_alerts],
    }
