FROM python:3.11-slim

# procps gives us `ps`/`sleep` etc for local debugging inside the container;
# systemd's client tools (systemctl/journalctl) are NOT installed here on
# purpose -- see README "Docker & host visibility" section for why the
# /services and /logs endpoints need special handling in Docker.
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# NOTE on the user below: psutil needs to read /proc entries for the
# processes it reports on and signal the ones it kills/restarts. Running
# as non-root is safer but means this container will only see/manage
# processes owned by 'sysmon' -- which, combined with --pid=host, is
# usually not very useful, since host processes are typically owned by
# other users or root. Read the README before deciding root vs non-root
# for your deployment; this Dockerfile defaults to root because that's
# the configuration that actually makes host-wide monitoring work, and
# the tradeoff should be a conscious choice, not a silent default.
# To run as non-root instead, uncomment the following two lines:
# RUN useradd -m sysmon
# USER sysmon

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
