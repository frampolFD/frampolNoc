import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime


class MonitoringStatus(str, enum.Enum):
    fully_monitored = "fully_monitored"
    icmp_only = "icmp_only"
    snmp_only = "snmp_only"
    monitoring_disabled = "monitoring_disabled"
    not_configured = "not_configured"


class SNMPVersion(str, enum.Enum):
    v2c = "v2c"
    v3 = "v3"  # structure supports it; MVP only implements v2c polling


class WANRole(str, enum.Enum):
    primary = "primary"
    backup = "backup"
    failover = "failover"
    load_balanced = "load_balanced"


class UserRole(str, enum.Enum):
    admin = "admin"
    engineer = "engineer"
    viewer = "viewer"


class AlertType(str, enum.Enum):
    wan_down = "wan_down"
    wan_recovered = "wan_recovered"
    high_latency = "high_latency"
    packet_loss = "packet_loss"
    sustained_utilisation = "sustained_utilisation"


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    primary_contact: Mapped[str | None] = mapped_column(String(200))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    contact_email: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now())

    cities: Mapped[list["City"]] = relationship(back_populates="customer", cascade="all, delete-orphan")


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("customer_id", "name", name="uq_city_customer_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="cities")
    suburbs: Mapped[list["Suburb"]] = relationship(back_populates="city", cascade="all, delete-orphan")
    branches: Mapped[list["Branch"]] = relationship(back_populates="city", cascade="all, delete-orphan")


class Suburb(Base):
    __tablename__ = "suburbs"
    __table_args__ = (UniqueConstraint("city_id", "name", name="uq_suburb_city_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    city: Mapped["City"] = relationship(back_populates="suburbs")
    branches: Mapped[list["Branch"]] = relationship(back_populates="suburb")


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False)
    suburb_id: Mapped[int | None] = mapped_column(ForeignKey("suburbs.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    physical_address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    primary_contact: Mapped[str | None] = mapped_column(String(200))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now())

    customer: Mapped["Customer"] = relationship()
    city: Mapped["City"] = relationship(back_populates="branches")
    suburb: Mapped["Suburb"] = relationship(back_populates="branches")
    wan_links: Mapped[list["WANLink"]] = relationship(back_populates="branch", cascade="all, delete-orphan")


class ISP(Base):
    __tablename__ = "isps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    badge_key: Mapped[str] = mapped_column(String(50), default="other")
    support_phone: Mapped[str | None] = mapped_column(String(50))
    noc_email: Mapped[str | None] = mapped_column(String(200))
    portal_url: Mapped[str | None] = mapped_column(String(500))
    escalation_contact: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    wan_links: Mapped[list["WANLink"]] = relationship(back_populates="isp")


class SNMPCredential(Base):
    """A named, encrypted SNMP credential. WAN links reference this by id
    rather than embedding a community string, so secrets never travel
    through the API, frontend bundle, or application logs."""

    __tablename__ = "snmp_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    version: Mapped[SNMPVersion] = mapped_column(Enum(SNMPVersion), default=SNMPVersion.v2c)
    encrypted_secret: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now())

    wan_links: Mapped[list["WANLink"]] = relationship(back_populates="snmp_credential")


class WANLink(Base):
    __tablename__ = "wan_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    isp_id: Mapped[int | None] = mapped_column(ForeignKey("isps.id"), nullable=True)

    name_generated: Mapped[str] = mapped_column(String(500), nullable=False)
    # Nullable: required for a monitored link (utilisation depends on it),
    # but an inventory-only/not-yet-configured link may not have one yet.
    # BigInteger: bps values for high-capacity circuits (10G+) exceed a
    # 32-bit PostgreSQL INTEGER.
    circuit_capacity_bps: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    role: Mapped[WANRole] = mapped_column(Enum(WANRole), default=WANRole.primary)
    public_ip: Mapped[str | None] = mapped_column(String(100))
    device_vendor: Mapped[str | None] = mapped_column(String(100))
    device_model: Mapped[str | None] = mapped_column(String(100))

    icmp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    icmp_target_ip: Mapped[str | None] = mapped_column(String(100))

    snmp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    snmp_target_ip: Mapped[str | None] = mapped_column(String(100))
    snmp_version: Mapped[SNMPVersion | None] = mapped_column(Enum(SNMPVersion), nullable=True)
    snmp_credential_id: Mapped[int | None] = mapped_column(ForeignKey("snmp_credentials.id"), nullable=True)

    selected_if_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_interface_name: Mapped[str | None] = mapped_column(String(200))
    selected_interface_ip: Mapped[str | None] = mapped_column(String(100))
    selected_interface_alias: Mapped[str | None] = mapped_column(String(200))

    monitoring_status: Mapped[MonitoringStatus] = mapped_column(Enum(MonitoringStatus), default=MonitoringStatus.not_configured)
    # Explicit "deliberately turned off" flag, distinct from icmp_enabled/
    # snmp_enabled simply being false because setup isn't finished yet. See
    # DECISIONS.md ("monitoring_disabled vs not_configured").
    monitoring_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    sustained_util_threshold_percent: Mapped[float] = mapped_column(Float, default=90.0)
    sustained_util_duration_seconds: Mapped[int] = mapped_column(Integer, default=600)

    # Null means "use the global default from SystemSettings" — only set
    # these to override polling cadence for this specific WAN link.
    icmp_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snmp_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now())

    branch: Mapped["Branch"] = relationship(back_populates="wan_links")
    isp: Mapped["ISP"] = relationship(back_populates="wan_links")
    snmp_credential: Mapped["SNMPCredential"] = relationship(back_populates="wan_links")
    interfaces: Mapped[list["SNMPInterface"]] = relationship(back_populates="wan_link", cascade="all, delete-orphan")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="wan_link", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="wan_link", cascade="all, delete-orphan")
    notes_entries: Mapped[list["EngineerNote"]] = relationship(back_populates="wan_link", cascade="all, delete-orphan")
    poll_state: Mapped["PollState"] = relationship(back_populates="wan_link", uselist=False, cascade="all, delete-orphan")


class SNMPInterface(Base):
    """Discovered interface metadata from a live SNMP walk of a WAN link's target."""

    __tablename__ = "snmp_interfaces"
    __table_args__ = (UniqueConstraint("wan_link_id", "if_index", name="uq_interface_wan_ifindex"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    wan_link_id: Mapped[int] = mapped_column(ForeignKey("wan_links.id"), nullable=False)
    if_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500))
    alias: Mapped[str | None] = mapped_column(String(200))
    ip_address: Mapped[str | None] = mapped_column(String(100))
    speed_bps: Mapped[int | None] = mapped_column(BigInteger)  # bps; a 32-bit Integer overflows on 10G+ interfaces
    mac_address: Mapped[str | None] = mapped_column(String(50))
    admin_status: Mapped[str | None] = mapped_column(String(20))
    oper_status: Mapped[str | None] = mapped_column(String(20))
    last_discovered_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now())

    wan_link: Mapped["WANLink"] = relationship(back_populates="interfaces")


class PollState(Base):
    """Last-known raw counters per WAN link, used to compute the next rate
    delta. Kept separate from Measurement (which is the timestamped history
    used for graphs) so we never have to scan history to find "the last
    sample" on every poll tick."""

    __tablename__ = "poll_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    wan_link_id: Mapped[int] = mapped_column(ForeignKey("wan_links.id"), nullable=False, unique=True)

    last_snmp_poll_at: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)
    # BigInteger: raw SNMP Counter64 values exceed a 32-bit PostgreSQL INTEGER.
    last_in_octets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_out_octets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    last_icmp_poll_at: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)

    utilisation_breach_since: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)
    is_down: Mapped[bool] = mapped_column(Boolean, default=False)

    wan_link: Mapped["WANLink"] = relationship(back_populates="poll_state")


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    wan_link_id: Mapped[int] = mapped_column(ForeignKey("wan_links.id"), nullable=False, index=True)
    timestamp: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now(), index=True)

    rx_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    tx_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    utilisation_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    rx_bytes_delta: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tx_bytes_delta: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    jitter_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    wan_link: Mapped["WANLink"] = relationship(back_populates="measurements")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    wan_link_id: Mapped[int] = mapped_column(ForeignKey("wan_links.id"), nullable=False, index=True)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now())
    ended_at: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)
    acknowledged_at: Mapped[object | None] = mapped_column(UTCDateTime(), nullable=True)
    acknowledged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    wan_link: Mapped["WANLink"] = relationship(back_populates="alerts")


class EngineerNote(Base):
    __tablename__ = "engineer_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    wan_link_id: Mapped[int] = mapped_column(ForeignKey("wan_links.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now())

    wan_link: Mapped["WANLink"] = relationship(back_populates="notes_entries")
    user: Mapped["User"] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.engineer)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now())


class SystemSettings(Base):
    """Single-row table of admin-editable global defaults.

    Always exactly one row (id=1). Per-WAN-link override columns on
    WANLink take precedence over these when set; these are the fallback.
    """

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    icmp_interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    snmp_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    updated_at: Mapped[object] = mapped_column(UTCDateTime(), server_default=func.now(), onupdate=func.now())
