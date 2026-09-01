from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.health import compute_health, compute_monitoring_status, latest_metrics
from app.models import (
    Alert,
    Branch,
    EngineerNote,
    ISP,
    Measurement,
    MonitoringStatus,
    SNMPCredential,
    SNMPInterface,
    User,
    WANLink,
)
from app.monitoring import snmp_client
from app.monitoring.scheduling import effective_interval
from app.monitoring.snmp_client import SNMPError
from app.monitoring.worker import poll_icmp_for_wan_link, poll_snmp_for_wan_link
from app.naming import generate_wan_name
from app.schemas import (
    AlertOut,
    DiscoveredInterfaceOut,
    EngineerNoteIn,
    EngineerNoteOut,
    InterfaceSelect,
    MeasurementOut,
    PollingIntervalsUpdate,
    SNMPInterfaceOut,
    WANLinkCreate,
    WANLinkOut,
    WANLinkWithHealth,
)
from app.security import decrypt_secret
from app.settings_store import get_or_create_settings

router = APIRouter(prefix="/api", tags=["wan-links"], dependencies=[Depends(get_current_user)])

HISTORY_RANGES = {
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "1m": timedelta(days=30),
    "1y": timedelta(days=365),
}


def _with_health(db: Session, wan_link: WANLink) -> WANLinkWithHealth:
    out = WANLinkWithHealth.model_validate(wan_link)
    out.isp_name = wan_link.isp.name if wan_link.isp else None
    out.isp_badge_key = wan_link.isp.badge_key if wan_link.isp else None
    out.health = compute_health(db, wan_link)
    out.latest = latest_metrics(db, wan_link)
    global_settings = get_or_create_settings(db)
    out.effective_icmp_interval_seconds = effective_interval(wan_link.icmp_interval_seconds, global_settings.icmp_interval_seconds)
    out.effective_snmp_interval_seconds = effective_interval(wan_link.snmp_interval_seconds, global_settings.snmp_interval_seconds)
    return out


@router.get("/branches/{branch_id}/wan-links", response_model=list[WANLinkWithHealth])
def list_wan_links_for_branch(branch_id: int, db: Session = Depends(get_db)):
    if not db.get(Branch, branch_id):
        raise HTTPException(status_code=404, detail="Branch not found")
    wan_links = db.query(WANLink).filter(WANLink.branch_id == branch_id).order_by(WANLink.id).all()
    return [_with_health(db, w) for w in wan_links]


@router.get("/wan-links/{wan_link_id}", response_model=WANLinkWithHealth)
def get_wan_link(wan_link_id: int, db: Session = Depends(get_db)):
    wan_link = db.get(WANLink, wan_link_id)
    if not wan_link:
        raise HTTPException(status_code=404, detail="WAN link not found")
    return _with_health(db, wan_link)


@router.delete("/wan-links/{wan_link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wan_link(wan_link_id: int, db: Session = Depends(get_db)):
    """Permanently removes a WAN link and everything tied to it (discovered
    interfaces, measurement history, alerts, engineer notes) via cascade."""
    wan_link = db.get(WANLink, wan_link_id)
    if not wan_link:
        raise HTTPException(status_code=404, detail="WAN link not found")
    db.delete(wan_link)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/wan-links", response_model=WANLinkOut)
def create_wan_link(payload: WANLinkCreate, db: Session = Depends(get_db)):
    branch = db.get(Branch, payload.branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    isp = db.get(ISP, payload.isp_id) if payload.isp_id else None
    if payload.snmp_enabled:
        if not payload.snmp_target_ip or not payload.snmp_credential_id:
            raise HTTPException(status_code=422, detail="SNMP target IP and credential are required when SNMP is enabled")
        if not db.get(SNMPCredential, payload.snmp_credential_id):
            raise HTTPException(status_code=404, detail="SNMP credential not found")
    if payload.icmp_enabled and not payload.icmp_target_ip:
        raise HTTPException(status_code=422, detail="ICMP target IP is required when ICMP is enabled")

    name = generate_wan_name(
        customer_name=branch.customer.name,
        city_name=branch.city.name,
        branch_name=branch.name,
        device_model=payload.device_model,
        isp_name=isp.name if isp else None,
        public_ip=payload.public_ip,
        circuit_capacity_bps=payload.circuit_capacity_bps,
    )

    wan_link = WANLink(
        **payload.model_dump(),
        name_generated=name,
        monitoring_status=compute_monitoring_status(payload.icmp_enabled, payload.snmp_enabled),
    )
    db.add(wan_link)
    db.commit()
    db.refresh(wan_link)
    return wan_link


@router.post("/wan-links/{wan_link_id}/discover", response_model=list[DiscoveredInterfaceOut])
async def discover_interfaces(wan_link_id: int, db: Session = Depends(get_db)):
    wan_link = db.get(WANLink, wan_link_id)
    if not wan_link:
        raise HTTPException(status_code=404, detail="WAN link not found")
    if not wan_link.snmp_enabled or not wan_link.snmp_target_ip or not wan_link.snmp_credential_id:
        raise HTTPException(status_code=422, detail="WAN link does not have SNMP target/credential configured")

    credential = db.get(SNMPCredential, wan_link.snmp_credential_id)
    if not credential:
        raise HTTPException(status_code=422, detail="SNMP credential not found")
    community = decrypt_secret(credential.encrypted_secret)

    try:
        discovered = await snmp_client.discover_interfaces(
            wan_link.snmp_target_ip,
            wan_link.snmp_version.value if wan_link.snmp_version else "v2c",
            community,
        )
    except SNMPError as exc:
        # Never let the exception surface the community string; SNMPError
        # messages only ever contain protocol-level detail (timeouts, OIDs).
        raise HTTPException(status_code=502, detail=f"SNMP discovery failed: {exc}") from exc
    finally:
        del community

    match_targets = {ip for ip in (wan_link.snmp_target_ip, wan_link.public_ip) if ip}

    # Persist discovered metadata so the engineer can revisit/reselect later
    # without re-running discovery, per DATABASE_DESIGN's SNMPInterface table.
    existing_by_index = {i.if_index: i for i in db.query(SNMPInterface).filter(SNMPInterface.wan_link_id == wan_link_id)}
    now = datetime.now(timezone.utc)
    results: list[DiscoveredInterfaceOut] = []
    for iface in discovered:
        row = existing_by_index.get(iface.if_index)
        if row is None:
            row = SNMPInterface(wan_link_id=wan_link_id, if_index=iface.if_index)
            db.add(row)
        row.name = iface.name
        row.description = iface.description
        row.alias = iface.alias
        row.ip_address = iface.ip_address
        row.speed_bps = iface.speed_bps
        row.mac_address = iface.mac_address
        row.admin_status = iface.admin_status
        row.oper_status = iface.oper_status
        row.last_discovered_at = now

        results.append(
            DiscoveredInterfaceOut(
                if_index=iface.if_index,
                name=iface.name,
                description=iface.description,
                alias=iface.alias,
                ip_address=iface.ip_address,
                speed_bps=iface.speed_bps,
                mac_address=iface.mac_address,
                admin_status=iface.admin_status,
                oper_status=iface.oper_status,
                suggested_match=iface.ip_address in match_targets if iface.ip_address else False,
            )
        )

    db.commit()
    return results


@router.get("/wan-links/{wan_link_id}/interfaces", response_model=list[SNMPInterfaceOut])
def list_discovered_interfaces(wan_link_id: int, db: Session = Depends(get_db)):
    return db.query(SNMPInterface).filter(SNMPInterface.wan_link_id == wan_link_id).order_by(SNMPInterface.if_index).all()


@router.post("/wan-links/{wan_link_id}/select-interface", response_model=WANLinkOut)
def select_interface(wan_link_id: int, payload: InterfaceSelect, db: Session = Depends(get_db)):
    """The engineer manually chooses which discovered interface represents
    this WAN. This never happens automatically, even if an IP matched."""
    wan_link = db.get(WANLink, wan_link_id)
    if not wan_link:
        raise HTTPException(status_code=404, detail="WAN link not found")

    interface = (
        db.query(SNMPInterface)
        .filter(SNMPInterface.wan_link_id == wan_link_id, SNMPInterface.if_index == payload.if_index)
        .first()
    )
    if not interface:
        raise HTTPException(status_code=404, detail="Interface not found in the most recent discovery — run discovery again")

    wan_link.selected_if_index = interface.if_index
    wan_link.selected_interface_name = interface.name or interface.description
    wan_link.selected_interface_ip = interface.ip_address
    wan_link.selected_interface_alias = interface.alias
    wan_link.monitoring_status = compute_monitoring_status(wan_link.icmp_enabled, wan_link.snmp_enabled)
    db.commit()
    db.refresh(wan_link)
    return wan_link


@router.patch("/wan-links/{wan_link_id}/polling-intervals", response_model=WANLinkWithHealth)
def update_polling_intervals(wan_link_id: int, payload: PollingIntervalsUpdate, db: Session = Depends(get_db)):
    """Set (or clear, by passing null) this WAN link's own ICMP/SNMP polling
    cadence. A null value falls back to the admin-configured global default
    on the next tick of the background worker."""
    wan_link = db.get(WANLink, wan_link_id)
    if not wan_link:
        raise HTTPException(status_code=404, detail="WAN link not found")
    for field in ("icmp_interval_seconds", "snmp_interval_seconds"):
        value = getattr(payload, field)
        if value is not None and value <= 0:
            raise HTTPException(status_code=422, detail=f"{field} must be a positive number of seconds")

    wan_link.icmp_interval_seconds = payload.icmp_interval_seconds
    wan_link.snmp_interval_seconds = payload.snmp_interval_seconds
    db.commit()
    db.refresh(wan_link)
    return _with_health(db, wan_link)


@router.post("/wan-links/{wan_link_id}/ping-now", response_model=WANLinkWithHealth)
async def ping_now(wan_link_id: int, db: Session = Depends(get_db)):
    wan_link = db.get(WANLink, wan_link_id)
    if not wan_link:
        raise HTTPException(status_code=404, detail="WAN link not found")
    if not wan_link.icmp_enabled:
        raise HTTPException(status_code=422, detail="ICMP is not enabled for this WAN link")
    await poll_icmp_for_wan_link(wan_link_id)
    db.refresh(wan_link)
    return _with_health(db, wan_link)


@router.post("/wan-links/{wan_link_id}/poll-now", response_model=WANLinkWithHealth)
async def poll_now(wan_link_id: int, db: Session = Depends(get_db)):
    wan_link = db.get(WANLink, wan_link_id)
    if not wan_link:
        raise HTTPException(status_code=404, detail="WAN link not found")
    if not wan_link.snmp_enabled or wan_link.selected_if_index is None:
        raise HTTPException(status_code=422, detail="SNMP interface is not configured for this WAN link")
    await poll_snmp_for_wan_link(wan_link_id)
    db.refresh(wan_link)
    return _with_health(db, wan_link)


@router.get("/wan-links/{wan_link_id}/measurements", response_model=list[MeasurementOut])
def get_measurements(wan_link_id: int, range: str = "1h", db: Session = Depends(get_db)):
    if range not in HISTORY_RANGES:
        raise HTTPException(status_code=422, detail=f"range must be one of {list(HISTORY_RANGES)}")
    since = datetime.now(timezone.utc) - HISTORY_RANGES[range]
    return (
        db.query(Measurement)
        .filter(Measurement.wan_link_id == wan_link_id, Measurement.timestamp >= since)
        .order_by(Measurement.timestamp.asc())
        .all()
    )


@router.get("/wan-links/{wan_link_id}/alerts", response_model=list[AlertOut])
def get_alerts(wan_link_id: int, db: Session = Depends(get_db)):
    return db.query(Alert).filter(Alert.wan_link_id == wan_link_id).order_by(Alert.started_at.desc()).all()


@router.post("/wan-links/{wan_link_id}/alerts/{alert_id}/ack", response_model=AlertOut)
def acknowledge_alert(wan_link_id: int, alert_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert = db.get(Alert, alert_id)
    if not alert or alert.wan_link_id != wan_link_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user.id
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/wan-links/{wan_link_id}/notes", response_model=list[EngineerNoteOut])
def list_notes(wan_link_id: int, db: Session = Depends(get_db)):
    return db.query(EngineerNote).filter(EngineerNote.wan_link_id == wan_link_id).order_by(EngineerNote.created_at.desc()).all()


@router.post("/wan-links/{wan_link_id}/notes", response_model=EngineerNoteOut)
def add_note(wan_link_id: int, payload: EngineerNoteIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.get(WANLink, wan_link_id):
        raise HTTPException(status_code=404, detail="WAN link not found")
    note = EngineerNote(wan_link_id=wan_link_id, user_id=user.id, body=payload.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
