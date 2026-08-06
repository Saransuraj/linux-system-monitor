"""
systemd service status checks and control, via `systemctl`.

Same injection-prevention approach as logs.py: never build a shell string,
always pass args as a list, always validate the service name first.
"""
import subprocess

from app.logs import _validate_service_name
from app.models import ProcessActionResult, ServiceStatus


def get_service_status(service: str) -> ServiceStatus:
    _validate_service_name(service)

    try:
        result = subprocess.run(
            ["systemctl", "show", service,
             "--property=ActiveState,SubState,Description,LoadState"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "systemctl not found. This feature requires systemd on the host "
            "and typically won't work unmodified inside a Docker container."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("systemctl timed out.")

    props = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            props[key] = value

    if props.get("LoadState") == "not-found":
        raise ValueError(f"Service {service!r} not found.")

    return ServiceStatus(
        name=service,
        active=props.get("ActiveState", "unknown"),
        sub_state=props.get("SubState", "unknown"),
        description=props.get("Description", ""),
        raw=result.stdout.strip(),
    )


def control_service(service: str, action: str) -> ProcessActionResult:
    """action must be one of: start, stop, restart"""
    _validate_service_name(service)
    if action not in ("start", "stop", "restart"):
        raise ValueError(f"Unsupported action: {action!r}")

    try:
        result = subprocess.run(
            ["systemctl", action, service],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        return ProcessActionResult(
            pid=0, action=action, success=False,
            message="systemctl not found on this host/container.",
        )
    except subprocess.TimeoutExpired:
        return ProcessActionResult(
            pid=0, action=action, success=False, message="systemctl timed out.",
        )

    success = result.returncode == 0
    message = result.stderr.strip() if not success else f"{service}: {action} succeeded."
    if not success and "Interactive authentication required" in result.stderr:
        message = (
            f"{service}: {action} failed -- requires elevated privileges (polkit/root). "
            f"The API process needs appropriate sudo/systemd permissions to control services."
        )
    return ProcessActionResult(pid=0, action=action, success=success, message=message)
