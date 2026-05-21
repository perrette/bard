"""Content-addressed cache for synthesized audio chunks.

Keyed by a deterministic fingerprint of (backend, model, voice, output_format,
text, plus any backend-specific extras). Lets us skip API calls when the same
text is re-rendered with the same settings. Intended for remote backends only
(local backends are gated by the caller).
"""
import hashlib
import json
import logging
import os
import shutil
import time
from pathlib import Path

logger = logging.getLogger("bard")


def _default_ttl() -> int:
    val = os.environ.get("BARD_CACHE_TTL_SECONDS")
    if val:
        try:
            parsed = int(val)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return 7 * 24 * 3600


DEFAULT_TTL_SECONDS = _default_ttl()


def _cache_root() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(xdg) / "bard" / "audio_cache"


def request_fingerprint(backend, text: str) -> str:
    """Deterministic hash of every input that affects the audio bytes."""
    voice = getattr(backend, "voice", None) or backend.default_voice
    model = getattr(backend, "model", None) or backend.default_model
    extras_fn = getattr(backend, "cache_fingerprint_extras", None)
    extras = extras_fn() if callable(extras_fn) else {}
    payload = {
        "backend": backend.name,
        "model": model,
        "voice": voice,
        "output_format": backend.output_format,
        "text": text,
        "extras": extras,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _entry_path(backend_name: str, key: str, ext: str) -> Path:
    return _cache_root() / backend_name / f"{key}.{ext}"


def try_load(backend_name: str, key: str, ext: str, out_path: Path, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    """If a fresh cache entry exists, copy it to out_path and refresh its mtime.
    Returns True on a hit.
    """
    src = _entry_path(backend_name, key, ext)
    try:
        age = time.time() - src.stat().st_mtime
    except FileNotFoundError:
        return False
    if age >= ttl_seconds:
        return False
    try:
        shutil.copyfile(src, out_path)
        os.utime(src, None)  # sliding TTL
        logger.debug("audio cache hit: %s", src.name)
        return True
    except OSError as e:
        logger.warning("audio cache hit but copy failed (%s); will re-synthesize", e)
        return False


def store(backend_name: str, key: str, ext: str, src_path: Path) -> None:
    """Copy src_path into the cache under the given key."""
    dst = _entry_path(backend_name, key, ext)
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dst)
    except OSError as e:
        logger.warning("audio cache store failed (%s)", e)


def clear_all() -> None:
    root = _cache_root()
    if root.exists():
        shutil.rmtree(root)
