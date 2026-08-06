from typing import Optional

from pydantic import BaseModel


class CpuUsage(BaseModel):
    percent_total: float
    percent_per_core: list[float]
    core_count: int
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float


class MemoryUsage(BaseModel):
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float
    swap_total_mb: float
    swap_used_mb: float
    swap_percent: float


class DiskPartition(BaseModel):
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class DiskUsage(BaseModel):
    partitions: list[DiskPartition]


class NetworkInterface(BaseModel):
    name: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int


class NetworkUsage(BaseModel):
    interfaces: list[NetworkInterface]


class ProcessInfo(BaseModel):
    pid: int
    name: str
    username: Optional[str]
    status: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    num_threads: int
    create_time: float
    cmdline: str


class ProcessActionResult(BaseModel):
    pid: int
    action: str
    success: bool
    message: str


class ServiceStatus(BaseModel):
    name: str
    active: str
    sub_state: str
    description: str
    raw: str


class LogLines(BaseModel):
    service: str
    lines: list[str]
    truncated: bool
