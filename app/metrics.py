"""
System metrics collection: CPU, memory, disk, network.

Uses psutil, which wraps /proc on Linux. CPU percentage requires two
samples separated by an interval to be meaningful (a single instant
reading is close to meaningless), so get_cpu_usage() blocks for
settings.CPU_SAMPLE_INTERVAL seconds by design.
"""
import os

import psutil

from app.config import settings
from app.models import (
    CpuUsage,
    DiskPartition,
    DiskUsage,
    MemoryUsage,
    NetworkInterface,
    NetworkUsage,
)


def get_cpu_usage() -> CpuUsage:
    per_core = psutil.cpu_percent(interval=settings.CPU_SAMPLE_INTERVAL, percpu=True)
    total = sum(per_core) / len(per_core) if per_core else 0.0
    load1, load5, load15 = os.getloadavg()
    return CpuUsage(
        percent_total=round(total, 2),
        percent_per_core=[round(c, 2) for c in per_core],
        core_count=psutil.cpu_count(logical=True) or 0,
        load_avg_1m=round(load1, 2),
        load_avg_5m=round(load5, 2),
        load_avg_15m=round(load15, 2),
    )


def get_memory_usage() -> MemoryUsage:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    mb = 1024 * 1024
    return MemoryUsage(
        total_mb=round(vm.total / mb, 2),
        used_mb=round(vm.used / mb, 2),
        available_mb=round(vm.available / mb, 2),
        percent=vm.percent,
        swap_total_mb=round(swap.total / mb, 2),
        swap_used_mb=round(swap.used / mb, 2),
        swap_percent=swap.percent,
    )


def get_disk_usage() -> DiskUsage:
    partitions = []
    gb = 1024 * 1024 * 1024
    for part in psutil.disk_partitions(all=False):
        # Skip pseudo/virtual filesystems that don't represent real storage.
        if part.fstype in ("", "squashfs", "tmpfs", "devtmpfs"):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        partitions.append(
            DiskPartition(
                device=part.device,
                mountpoint=part.mountpoint,
                fstype=part.fstype,
                total_gb=round(usage.total / gb, 2),
                used_gb=round(usage.used / gb, 2),
                free_gb=round(usage.free / gb, 2),
                percent=usage.percent,
            )
        )
    return DiskUsage(partitions=partitions)


def get_network_usage() -> NetworkUsage:
    counters = psutil.net_io_counters(pernic=True)
    interfaces = [
        NetworkInterface(
            name=name,
            bytes_sent=c.bytes_sent,
            bytes_recv=c.bytes_recv,
            packets_sent=c.packets_sent,
            packets_recv=c.packets_recv,
            errin=c.errin,
            errout=c.errout,
        )
        for name, c in counters.items()
    ]
    return NetworkUsage(interfaces=interfaces)
