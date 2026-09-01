"""Pure polling-cadence resolution: per-WAN-link override wins, otherwise
fall back to the admin-configured global default."""


def effective_interval(override_seconds: int | None, global_default_seconds: int) -> int:
    if override_seconds is not None and override_seconds > 0:
        return override_seconds
    return global_default_seconds
