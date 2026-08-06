"""
Unit tests for app/processes.py.

Kill/restart are tested against a real short-lived subprocess we spawn
ourselves in the test (a `sleep` call), so the test owns the process
being killed and doesn't touch anything else running on the machine.
"""
import subprocess
import time

from app import processes


def _spawn_sleep():
    proc = subprocess.Popen(["sleep", "30"])
    time.sleep(0.1)  # let it register with psutil
    return proc


def test_list_processes_returns_entries():
    result = processes.list_processes()
    assert isinstance(result, list)
    assert len(result) > 0
    assert any(p.pid == 1 or p.name for p in result)


def test_kill_process_success():
    proc = _spawn_sleep()
    result = processes.kill_process(proc.pid)
    assert result.success is True
    proc.wait(timeout=5)
    assert proc.poll() is not None


def test_kill_nonexistent_process():
    result = processes.kill_process(999999)
    assert result.success is False


def test_restart_process_reexecs_command():
    proc = _spawn_sleep()
    result = processes.restart_process(proc.pid)
    assert result.success is True
    assert result.pid != proc.pid  # new process, new pid
    # Clean up the replacement process.
    processes.kill_process(result.pid, force=True)
