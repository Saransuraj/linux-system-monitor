"""
Unit tests for app/metrics.py.

These run against the real host psutil data (fast, since the CPU sample
interval is monkeypatched to 0 for speed) rather than mocking /proc,
since psutil already abstracts that layer -- we're testing our wrapping
logic, not psutil itself.
"""
from app import metrics
from app.config import settings


def test_get_cpu_usage_shape(monkeypatch):
    monkeypatch.setattr(settings, "CPU_SAMPLE_INTERVAL", 0.05)
    result = metrics.get_cpu_usage()
    assert 0.0 <= result.percent_total <= 100.0
    assert result.core_count >= 1
    assert len(result.percent_per_core) == result.core_count
    assert result.load_avg_1m >= 0.0


def test_get_memory_usage_shape():
    result = metrics.get_memory_usage()
    assert result.total_mb > 0
    assert 0.0 <= result.percent <= 100.0
    assert result.used_mb <= result.total_mb + 1  # small slack for rounding


def test_get_disk_usage_shape():
    result = metrics.get_disk_usage()
    assert isinstance(result.partitions, list)
    for part in result.partitions:
        assert part.total_gb >= 0
        assert 0.0 <= part.percent <= 100.0


def test_get_network_usage_shape():
    result = metrics.get_network_usage()
    assert isinstance(result.interfaces, list)
    for iface in result.interfaces:
        assert iface.bytes_sent >= 0
        assert iface.bytes_recv >= 0
