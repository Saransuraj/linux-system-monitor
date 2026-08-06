# Linux System Monitoring & Process Manager

A REST API (FastAPI) for monitoring Linux system resources and managing
processes/services, built with `psutil`, `systemctl`, and `journalctl`.

## Features

- CPU, RAM, disk, network usage
- Running process list, kill, restart
- Log viewer (via `journalctl`)
- systemd service status + start/stop/restart
- API key authentication on all non-health endpoints
- Docker support

## Quick start (local, no Docker)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set SYSMON_API_KEY to a real secret

export $(cat .env | xargs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs for interactive Swagger UI.

Every endpoint except `/health` requires an `X-API-Key` header matching
`SYSMON_API_KEY`:

```bash
curl -H "X-API-Key: your-secret" http://localhost:8000/metrics/cpu
```

## Running tests

```bash
pytest tests/ -v
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

### ⚠️ Docker & host visibility — read this before deploying

A container has its **own PID namespace** by default. That means `psutil`
running inside a plain container only sees the container's own processes
— not the host's. To monitor the actual host, `docker-compose.yml` sets
`pid: host`, which shares the host's PID namespace with the container.

This has real security implications: a container with host PID visibility
can see (and, if privileged, signal) processes belonging to the host and
other users. Don't run this in `privileged: true` mode unless you've
deliberately decided you need cross-user kill/restart and accepted the
risk. For most use cases, `pid: host` alone (without `privileged`) is
enough to *monitor* the host; killing processes you don't own will still
correctly fail with a permission error, which is the safe default.

### ⚠️ `/logs` and `/services` endpoints need systemd

`journalctl` and `systemctl` are systemd client tools. They are **not**
installed in the slim Docker image on purpose, because a minimal
container typically doesn't run systemd. If you need these endpoints
to work from inside Docker, you have two realistic options:

1. Run the API directly on the host (not in Docker) for these specific
   features, or
2. Mount the host's `/run/systemd` and `/var/log/journal` into the
   container and install `systemd`'s client tools in the image — this
   is finicky and not enabled by default here; treat it as a follow-up
   task, not an assumption baked into this build.

## Permission model for kill/restart

This API can only signal (kill/restart) processes that the user it runs
as actually owns, unless it runs as root. Running as root makes the
"kill any process" feature actually work, but it also means a
compromised or misused API key can kill *anything* on the host,
including this API's own supervisor. Pick deliberately:

- **Non-root user**: safer, but effectively limits process management to
  processes started by that same user (or by this API itself). Good fit
  if this tool mainly manages its own supervised processes.
- **Root**: full process control, but you must treat `SYSMON_API_KEY`
  with the same care as a root credential — restrict network exposure,
  rotate it, don't commit it, put the API behind TLS if it leaves
  localhost.

The Dockerfile defaults to root for this reason and documents the
non-root alternative inline — flip it once you've decided which model
fits your deployment.

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check (no auth) |
| GET | `/metrics/cpu` | CPU % (total + per-core), load average |
| GET | `/metrics/memory` | RAM + swap usage |
| GET | `/metrics/disk` | Per-partition disk usage |
| GET | `/metrics/network` | Per-interface network counters |
| GET | `/processes` | List all visible processes |
| POST | `/processes/{pid}/kill?force=false` | SIGTERM (or SIGKILL if `force=true`) |
| POST | `/processes/{pid}/restart` | Kill + re-exec original command (see limitations below) |
| GET | `/logs/{service}?lines=100` | Recent `journalctl` output for a systemd unit |
| GET | `/services/{name}/status` | `systemctl show` summary |
| POST | `/services/{name}/{start\|stop\|restart}` | Control a systemd service |

## Known limitations (by design, not bugs)

- **`restart_process` is best-effort.** It captures `cmdline`/`cwd`/`env`
  before killing, then re-execs. This works for simple long-running
  processes but will not correctly restart anything supervised by
  systemd (use `/services/{name}/restart` for those), anything relying
  on inherited file descriptors/sockets, or shell pipelines.
- **CPU % requires a blocking sample window** (`SYSMON_CPU_INTERVAL`,
  default 0.5s) — the `/metrics/cpu` endpoint will take at least that
  long to respond. This is a correctness tradeoff, not a bug: an
  instantaneous CPU reading from `psutil`/`/proc` is not meaningful.
- **Service name validation is an allow-list regex** plus an optional
  `SYSMON_ALLOWED_SERVICES` whitelist — set the whitelist in production
  so the log/service endpoints can't be pointed at arbitrary units.

## Project structure

```
app/
  main.py        FastAPI app + routes
  config.py      Environment-based settings
  auth.py        API key dependency
  metrics.py     CPU/RAM/disk/network (psutil)
  processes.py   Process list/kill/restart (psutil)
  logs.py        journalctl wrapper
  services.py    systemctl wrapper
  models.py      Pydantic response models
tests/
  test_metrics.py
  test_processes.py
Dockerfile
docker-compose.yml
requirements.txt
.env.example
```
