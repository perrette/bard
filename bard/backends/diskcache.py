import json
import os
import shutil
import time
from pathlib import Path
from typing import Any


def _default_ttl() -> int:
    val = os.environ.get("BARD_CACHE_TTL_SECONDS")
    if val:
        try:
            parsed = int(val)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return 604800


DEFAULT_TTL_SECONDS = _default_ttl()


def _cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(xdg) / "bard" / "api_cache"


def load(backend: str, key: str, ttl_seconds: int) -> Any | None:
    path = _cache_dir() / backend / f"{key}.json"
    try:
        with open(path) as f:
            entry = json.load(f)
        if time.time() - entry["fetched_at"] < ttl_seconds:
            return entry["data"]
    except Exception:
        pass
    return None


def save(backend: str, key: str, data: Any) -> None:
    path = _cache_dir() / backend / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"fetched_at": int(time.time()), "data": data}, f)


def clear_all() -> None:
    cache = _cache_dir()
    if cache.exists():
        shutil.rmtree(cache)
