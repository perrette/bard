"""Locate TTS model files across XDG-standard and legacy directories.

Search order for a given subdir (e.g. ``piper``, ``kokoro``):

1. ``$XDG_DATA_HOME/<subdir>``               (default ``~/.local/share/<subdir>``)
2. ``$XDG_DATA_HOME/bard/<subdir>``
3. ``$XDG_DATA_DIRS/<subdir>``               (default ``/usr/local/share``, ``/usr/share``)
4. ``$XDG_CACHE_HOME/bard/<subdir>``         (legacy ``~/.cache/bard/<subdir>``)

The shared location comes first so an installation reused by multiple tools
is preferred over a bard-private copy.
"""
import os
from pathlib import Path

HOME = Path.home()
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share")
XDG_DATA_DIRS = tuple(
    Path(p) for p in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    if p
)
XDG_CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache")


def search_dirs(subdir: str) -> list[Path]:
    return [
        XDG_DATA_HOME / subdir,
        XDG_DATA_HOME / "bard" / subdir,
        *(d / subdir for d in XDG_DATA_DIRS),
        XDG_CACHE_HOME / "bard" / subdir,
    ]


def find_model_file(subdir: str, filename: str) -> Path | None:
    for d in search_dirs(subdir):
        p = d / filename
        if p.exists():
            return p
    return None


def default_model_dir(subdir: str) -> Path:
    return XDG_DATA_HOME / subdir


def resolve_model_path(
    env_var: str,
    subdir: str,
    filename: str,
    explicit: str | os.PathLike | None = None,
) -> Path:
    """Resolve a model file path.

    Explicit argument and environment variable are returned as-is (existence
    is the caller's responsibility). Otherwise, search the candidate dirs
    and return the first hit, or the recommended download path if none match.
    """
    if explicit:
        return Path(explicit)
    env = os.environ.get(env_var)
    if env:
        return Path(env)
    found = find_model_file(subdir, filename)
    if found is not None:
        return found
    return default_model_dir(subdir) / filename
