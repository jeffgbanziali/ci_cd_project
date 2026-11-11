"""Simulation de pannes temporaires, pour DÉMONTRER les mécanismes de retry.

    SIMULATE_DB_FAILURES=2  -> les 2 premières insertions en base échouent
    SIMULATE_S3_FAILURES=2  -> les 2 premiers téléchargements S3 échouent
"""
import os
import threading

from src.errors import TransientError

_lock = threading.Lock()
_remaining: dict[str, int] = {}


def configure(name: str, failures: int) -> None:
    with _lock:
        _remaining[name] = failures


def reset() -> None:
    with _lock:
        _remaining.clear()


def maybe_fail(name: str) -> None:
    with _lock:
        if name not in _remaining:
            _remaining[name] = int(os.getenv(f"SIMULATE_{name.upper()}_FAILURES", "0"))
        if _remaining[name] > 0:
            _remaining[name] -= 1
            raise TransientError(
                f"[simulation] panne temporaire '{name}' (il en reste {_remaining[name]})"
            )
