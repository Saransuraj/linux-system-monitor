"""
Linux System Monitoring & Process Manager -- FastAPI app.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Docs:
    http://localhost:8000/docs

All endpoints except /health require the 'X-API-Key' header
(see app/config.py / .env.example for setting the key).
"""
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app import logs as logs_module
from app import metrics as metrics_module
from app import processes as processes_module
from app import services as services_module
from app.auth import require_api_key
from app.models import (
    CpuUsage,
    DiskUsage,
    LogLines,
    MemoryUsage,
    NetworkUsage,
    ProcessActionResult,
    ProcessInfo,
    ServiceStatus,
)

app = FastAPI(
    title="Linux System Monitoring & Process Manager",
    description="REST API for monitoring system resources and managing processes/services on Linux.",
    version="1.0.0",
)


@app.get("/health", tags=["health"])
def health():
    """Unauthenticated liveness check."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@app.get("/metrics/cpu", response_model=CpuUsage, tags=["metrics"], dependencies=[Depends(require_api_key)])
def cpu_usage():
    return metrics_module.get_cpu_usage()


@app.get("/metrics/memory", response_model=MemoryUsage, tags=["metrics"], dependencies=[Depends(require_api_key)])
def memory_usage():
    return metrics_module.get_memory_usage()


@app.get("/metrics/disk", response_model=DiskUsage, tags=["metrics"], dependencies=[Depends(require_api_key)])
def disk_usage():
    return metrics_module.get_disk_usage()


@app.get("/metrics/network", response_model=NetworkUsage, tags=["metrics"], dependencies=[Depends(require_api_key)])
def network_usage():
    return metrics_module.get_network_usage()


# ---------------------------------------------------------------------------
# Processes
# ---------------------------------------------------------------------------

@app.get("/processes", response_model=list[ProcessInfo], tags=["processes"], dependencies=[Depends(require_api_key)])
def list_processes():
    return processes_module.list_processes()


@app.post(
    "/processes/{pid}/kill",
    response_model=ProcessActionResult,
    tags=["processes"],
    dependencies=[Depends(require_api_key)],
)
def kill_process(pid: int, force: bool = Query(default=False, description="Send SIGKILL immediately instead of SIGTERM first")):
    result = processes_module.kill_process(pid, force=force)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@app.post(
    "/processes/{pid}/restart",
    response_model=ProcessActionResult,
    tags=["processes"],
    dependencies=[Depends(require_api_key)],
)
def restart_process(pid: int):
    result = processes_module.restart_process(pid)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@app.get("/logs/{service}", response_model=LogLines, tags=["logs"], dependencies=[Depends(require_api_key)])
def service_logs(service: str, lines: int = Query(default=100, ge=1, le=2000)):
    try:
        return logs_module.get_service_logs(service, lines=lines)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

@app.get("/services/{name}/status", response_model=ServiceStatus, tags=["services"], dependencies=[Depends(require_api_key)])
def service_status(name: str):
    try:
        return services_module.get_service_status(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/services/{name}/{action}",
    response_model=ProcessActionResult,
    tags=["services"],
    dependencies=[Depends(require_api_key)],
)
def service_control(name: str, action: str):
    if action not in ("start", "stop", "restart"):
        raise HTTPException(status_code=400, detail="action must be start, stop, or restart")
    result = services_module.control_service(name, action)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
