"""
Log viewer, backed by `journalctl` (systemd's log store), which is the
standard/robust source for service logs on Ubuntu -- more reliable than
grepping /var/log/*.log files, whose naming and rotation vary per service.

Security note: service names are used as subprocess arguments, never
interpolated into a shell string, and are validated against a strict
allow-list pattern before use. This prevents command injection via a
crafted service name (e.g. "nginx; rm -rf /").
"""
import re
import subprocess

from app.config import settings
from app.models import LogLines

# Systemd unit names: letters, digits, ':-_.\@' -- deliberately conservative.
_SERVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9:_.@-]+$")


def _validate_service_name(name: str) -> None:
    if not _SERVICE_NAME_RE.match(name):
        raise ValueError(f"Invalid service name: {name!r}")
    if settings.ALLOWED_SERVICES and name not in settings.ALLOWED_SERVICES:
        raise ValueError(
            f"Service {name!r} is not in the allowed list "
            f"(SYSMON_ALLOWED_SERVICES)."
        )


def get_service_logs(service: str, lines: int = 100) -> LogLines:
    _validate_service_name(service)
    lines = min(lines, settings.MAX_LOG_LINES)

    try:
        result = subprocess.run(
            ["journalctl", "-u", service, "-n", str(lines), "--no-pager", "-o", "short-iso"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "journalctl not found. This feature requires systemd and is "
            "typically unavailable inside minimal Docker containers -- "
            "run with access to the host's systemd/journal, or fall back "
            "to reading files under /var/log directly."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("journalctl timed out.")

    if result.returncode != 0:
        raise RuntimeError(f"journalctl failed: {result.stderr.strip()}")

    output_lines = result.stdout.splitlines()
    return LogLines(
        service=service,
        lines=output_lines,
        truncated=len(output_lines) >= lines,
    )
