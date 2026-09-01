from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import AlertSeverity, AlertType, MonitoringStatus, SNMPVersion, UserRole, WANRole


class CustomerIn(BaseModel):
    name: str
    status: str = "active"
    primary_contact: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None


class CustomerOut(CustomerIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CityIn(BaseModel):
    name: str
    province: str
    country_code: str = "ZW"
    latitude: float | None = None
    longitude: float | None = None


class CityOut(CityIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SuburbIn(BaseModel):
    city_id: int
    name: str


class SuburbOut(SuburbIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BranchIn(BaseModel):
    customer_id: int
    city_id: int
    suburb_id: int | None = None
    name: str
    physical_address: str | None = None
    latitude: float
    longitude: float
    primary_contact: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


class BranchOut(BranchIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ISPIn(BaseModel):
    name: str
    badge_key: str = "other"
    support_phone: str | None = None
    noc_email: str | None = None
    portal_url: str | None = None
    escalation_contact: str | None = None
    notes: str | None = None


class ISPOut(ISPIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SNMPCredentialIn(BaseModel):
    name: str
    version: SNMPVersion = SNMPVersion.v2c
    community: str = Field(..., description="Plaintext community string; encrypted at rest, never returned by the API")


class SNMPCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    version: SNMPVersion


class WANLinkCreate(BaseModel):
    branch_id: int
    isp_id: int | None = None
    circuit_capacity_bps: int | None = Field(
        None,
        gt=0,
        description="Required once ICMP or SNMP monitoring is enabled; may be left unset for inventory-only links",
    )
    role: WANRole = WANRole.primary
    public_ip: str | None = None
    device_vendor: str | None = None
    device_model: str | None = None
    notes: str | None = None

    icmp_enabled: bool = False
    icmp_target_ip: str | None = None

    snmp_enabled: bool = False
    snmp_target_ip: str | None = None
    snmp_version: SNMPVersion | None = None
    snmp_credential_id: int | None = None

    monitoring_disabled: bool = Field(
        False, description="Deliberately no monitoring for this link (e.g. customer doesn't permit it) — distinct from not-yet-configured"
    )

    sustained_util_threshold_percent: float = 90.0
    sustained_util_duration_seconds: int = 600

    icmp_interval_seconds: int | None = Field(None, description="Override the global ICMP polling interval; null uses the admin default")
    snmp_interval_seconds: int | None = Field(None, description="Override the global SNMP polling interval; null uses the admin default")


class PollingIntervalsUpdate(BaseModel):
    icmp_interval_seconds: int | None = None
    snmp_interval_seconds: int | None = None


class SystemSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    icmp_interval_seconds: int
    snmp_interval_seconds: int


class SystemSettingsUpdate(BaseModel):
    icmp_interval_seconds: int = Field(..., gt=0)
    snmp_interval_seconds: int = Field(..., gt=0)


class InterfaceSelect(BaseModel):
    if_index: int


class DiscoverRequest(BaseModel):
    snmp_target_ip: str
    snmp_version: SNMPVersion = SNMPVersion.v2c
    snmp_credential_id: int


class DiscoveredInterfaceOut(BaseModel):
    if_index: int
    name: str | None
    description: str | None
    alias: str | None
    ip_address: str | None
    speed_bps: int | None
    mac_address: str | None
    admin_status: str | None
    oper_status: str | None
    suggested_match: bool = False


class SNMPInterfaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    if_index: int
    name: str | None
    description: str | None
    alias: str | None
    ip_address: str | None
    speed_bps: int | None
    mac_address: str | None
    admin_status: str | None
    oper_status: str | None


class WANLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    branch_id: int
    isp_id: int | None
    name_generated: str
    circuit_capacity_bps: int | None
    role: WANRole
    public_ip: str | None
    device_vendor: str | None
    device_model: str | None
    icmp_enabled: bool
    icmp_target_ip: str | None
    snmp_enabled: bool
    snmp_target_ip: str | None
    snmp_version: SNMPVersion | None
    selected_if_index: int | None
    selected_interface_name: str | None
    selected_interface_ip: str | None
    selected_interface_alias: str | None
    monitoring_status: MonitoringStatus
    monitoring_disabled: bool
    notes: str | None
    sustained_util_threshold_percent: float
    sustained_util_duration_seconds: int
    icmp_interval_seconds: int | None
    snmp_interval_seconds: int | None


class LatestMetrics(BaseModel):
    rx_bps: float | None = None
    tx_bps: float | None = None
    total_bps: float | None = None
    utilisation_percent: float | None = None
    latency_ms: float | None = None
    packet_loss_percent: float | None = None
    jitter_ms: float | None = None
    availability: bool | None = None
    last_snmp_poll_at: datetime | None = None
    last_icmp_poll_at: datetime | None = None


class WANLinkWithHealth(WANLinkOut):
    isp_name: str | None = None
    isp_badge_key: str | None = None
    health: str = "unknown"
    latest: LatestMetrics = LatestMetrics()
    effective_icmp_interval_seconds: int = 30
    effective_snmp_interval_seconds: int = 60


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: datetime
    rx_bps: float | None
    tx_bps: float | None
    total_bps: float | None
    utilisation_percent: float | None
    rx_bytes_delta: int | None
    tx_bytes_delta: int | None
    latency_ms: float | None
    packet_loss_percent: float | None
    jitter_ms: float | None
    availability: bool | None


class EngineerNoteIn(BaseModel):
    body: str


class EngineerNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    body: str
    created_at: datetime
    user_id: int | None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_type: AlertType
    severity: AlertSeverity
    threshold: float | None
    duration_seconds: int | None
    started_at: datetime
    ended_at: datetime | None
    acknowledged_at: datetime | None
    message: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: UserRole
