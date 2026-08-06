"""
Application configuration, loaded from environment variables.
"""
import os


class Settings:
    # API key required in the 'X-API-Key' header for all endpoints,
    # and mandatory for destructive endpoints (kill/restart).
    API_KEY: str = os.getenv("SYSMON_API_KEY", "change-me")

    # Sampling interval (seconds) used when computing CPU percentage.
    # psutil needs two samples to compute a meaningful percentage;
    # a value of 0 returns an instantaneous (often inaccurate) reading.
    CPU_SAMPLE_INTERVAL: float = float(os.getenv("SYSMON_CPU_INTERVAL", "0.5"))

    # Whitelist of systemd services that can be queried for status/logs.
    # Empty list = no restriction (not recommended in production).
    ALLOWED_SERVICES: list[str] = [
        s.strip() for s in os.getenv("SYSMON_ALLOWED_SERVICES", "").split(",") if s.strip()
    ]

    # Max number of log lines returned by the log viewer in one call.
    MAX_LOG_LINES: int = int(os.getenv("SYSMON_MAX_LOG_LINES", "500"))


settings = Settings()
