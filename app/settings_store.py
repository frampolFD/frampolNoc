from sqlalchemy.orm import Session

from app.config import settings as env_settings
from app.models import SystemSettings

SETTINGS_ROW_ID = 1


def get_or_create_settings(db: Session) -> SystemSettings:
    """The single admin-editable settings row, bootstrapped from the
    environment-configured defaults the first time it's read."""
    row = db.get(SystemSettings, SETTINGS_ROW_ID)
    if row:
        return row
    row = SystemSettings(
        id=SETTINGS_ROW_ID,
        icmp_interval_seconds=env_settings.icmp_interval_seconds,
        snmp_interval_seconds=env_settings.snmp_interval_seconds,
    )
    db.add(row)
    db.flush()
    return row
