from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env file.

    Nothing sensitive (SNMP communities, session secret, admin password) ever
    has a real-looking default here — production values must come from the
    environment so secrets never end up committed or in the frontend bundle.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="FRAMPOL_", extra="ignore")

    database_url: str = "sqlite:///./frampol_noc.db"

    session_secret_key: str = "dev-only-insecure-secret-change-me"
    credential_key: str = "dev-only-insecure-credential-key-change-me"

    # Dev/demo convenience only — skips the login screen and auto-authenticates
    # as the seeded admin. Defaults off; never enable this on anything
    # reachable outside your own machine.
    skip_auth: bool = False

    admin_email: str = "admin@frampol.local"
    admin_password: str = "changeme123"

    icmp_interval_seconds: int = 30
    icmp_count_per_poll: int = 4
    icmp_timeout_seconds: int = 2

    snmp_interval_seconds: int = 60
    snmp_timeout_seconds: int = 3
    snmp_retries: int = 1

    high_latency_threshold_ms: float = 150.0
    packet_loss_threshold_percent: float = 10.0

    default_sustained_utilisation_threshold_percent: float = 90.0
    default_sustained_utilisation_duration_seconds: int = 600


settings = Settings()
