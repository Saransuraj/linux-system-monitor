"""
Process listing and lifecycle management (kill / restart).

Important limitations, documented rather than hidden:

1. Permissions: this process can only signal processes owned by the same
   user it runs as (unless it runs as root, which is a security tradeoff
   you should make deliberately -- see README).

2. "Restart" is not a real OS concept. To restart a process we capture
   its command line, working directory, and environment *before* killing
   it, then re-exec that exact command. This works for simple long-running
   processes (e.g. a script or server started directly) but will NOT
   correctly restart processes that are supervised by systemd, that were
   started with shell pipelines/redirection, or that depend on runtime
   state not visible in argv/env (open sockets, parent-child relationships,
   etc). For anything managed by systemd, use the /services endpoints
   (systemctl restart) instead -- that's the correct tool for that job.
"""
import os
import signal
import subprocess
import time

import psutil

from app.models import ProcessActionResult, ProcessInfo


def list_processes() -> list[ProcessInfo]:
    processes = []
    for p in psutil.process_iter(
        ["pid", "name", "username", "status", "cpu_percent", "memory_percent",
         "memory_info", "num_threads", "create_time", "cmdline"]
    ):
        try:
            info = p.info
            mem_info = info.get("memory_info")
            processes.append(
                ProcessInfo(
                    pid=info["pid"],
                    name=info["name"] or "",
                    username=info.get("username"),
                    status=info.get("status", ""),
                    cpu_percent=info.get("cpu_percent") or 0.0,
                    memory_percent=round(info.get("memory_percent") or 0.0, 2),
                    memory_mb=round((mem_info.rss / (1024 * 1024)) if mem_info else 0.0, 2),
                    num_threads=info.get("num_threads") or 0,
                    create_time=info.get("create_time") or 0.0,
                    cmdline=" ".join(info.get("cmdline") or []),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process exited mid-scan, or we don't have permission to read it.
            # Skip rather than fail the whole listing.
            continue
    return processes


def get_process(pid: int) -> psutil.Process:
    try:
        return psutil.Process(pid)
    except psutil.NoSuchProcess:
        raise ValueError(f"No process with pid {pid}")


def kill_process(pid: int, force: bool = False, timeout: float = 3.0) -> ProcessActionResult:
    try:
        proc = get_process(pid)
        proc_name = proc.name()
    except ValueError as e:
        return ProcessActionResult(pid=pid, action="kill", success=False, message=str(e))

    try:
        if force:
            proc.send_signal(signal.SIGKILL)
        else:
            proc.terminate()  # SIGTERM
            try:
                proc.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                proc.kill()  # escalate to SIGKILL
        return ProcessActionResult(
            pid=pid, action="kill", success=True,
            message=f"Process {pid} ({proc_name}) terminated.",
        )
    except psutil.AccessDenied:
        return ProcessActionResult(
            pid=pid, action="kill", success=False,
            message=f"Permission denied killing pid {pid}. "
                    f"The API process does not own this process.",
        )
    except psutil.NoSuchProcess:
        return ProcessActionResult(
            pid=pid, action="kill", success=True,
            message=f"Process {pid} already gone.",
        )


def restart_process(pid: int, timeout: float = 3.0) -> ProcessActionResult:
    try:
        proc = get_process(pid)
        cmdline = proc.cmdline()
        cwd = proc.cwd()
        env = proc.environ()
    except ValueError as e:
        return ProcessActionResult(pid=pid, action="restart", success=False, message=str(e))
    except psutil.AccessDenied:
        return ProcessActionResult(
            pid=pid, action="restart", success=False,
            message=f"Permission denied reading process {pid} details "
                    f"(cmdline/cwd/env). Cannot safely restart.",
        )

    if not cmdline:
        return ProcessActionResult(
            pid=pid, action="restart", success=False,
            message=f"Process {pid} has no readable command line; cannot restart. "
                    f"If this is a systemd service, use POST /services/{{name}}/restart instead.",
        )

    kill_result = kill_process(pid, timeout=timeout)
    if not kill_result.success:
        return ProcessActionResult(
            pid=pid, action="restart", success=False,
            message=f"Could not stop process before restart: {kill_result.message}",
        )

    time.sleep(0.2)  # brief grace period before re-exec

    try:
        new_proc = subprocess.Popen(
            cmdline,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ProcessActionResult(
            pid=new_proc.pid, action="restart", success=True,
            message=f"Restarted as new pid {new_proc.pid} "
                    f"(original pid {pid} command: {' '.join(cmdline)}).",
        )
    except OSError as e:
        return ProcessActionResult(
            pid=pid, action="restart", success=False,
            message=f"Process {pid} was stopped but re-exec failed: {e}",
        )
