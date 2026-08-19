"""Shared config loading, consolidated out of service_a.py and service_b.py.

Both services previously had near-identical `load_config()` functions that
read from environment variables with slightly different defaults. This
module unifies them behind one implementation.
"""
import os
from dataclasses import dataclass


@dataclass
class ServiceConfig:
    log_level: str
    max_workers: int
    timeout_seconds: float


def load_config(prefix: str) -> ServiceConfig:
    """Load config for a service from `{PREFIX}_*` environment variables."""
    return ServiceConfig(
        log_level=os.environ.get(f"{prefix}_LOG_LEVEL", "INFO"),
        max_workers=int(os.environ.get(f"{prefix}_MAX_WORKERS", "4")),
        timeout_seconds=float(os.environ.get(f"{prefix}_TIMEOUT_SECONDS", "30")),
    )
