"""Helpers for grouping voices by language and resolving a --language filter."""
from collections import OrderedDict
from typing import Iterable

from desktop_ai_core.providers import Voice


def group_by_language(voices: Iterable[Voice]) -> "OrderedDict[str | None, list[Voice]]":
    """Return voices grouped by their `language` attribute, preserving input order."""
    groups: "OrderedDict[str | None, list[Voice]]" = OrderedDict()
    for v in voices:
        groups.setdefault(v.language, []).append(v)
    return groups


def _normalize(lang: str) -> str:
    return lang.lower().replace("_", "-")


def matches_language(voice_language: str | None, requested: str) -> bool:
    """Match a `--language` filter against a voice's language tag.

    Either side may be a bare ISO code (`fr`) or a country-suffixed tag
    (`fr-FR`). A bare filter matches any country variant; a suffixed filter
    requires the exact tag.
    """
    if not voice_language:
        return False
    v = _normalize(voice_language)
    r = _normalize(requested)
    if "-" in r:
        return v == r
    return v == r or v.startswith(r + "-")


def find_first_for_language(voices: Iterable[Voice], requested: str) -> Voice | None:
    """Return the first voice in `voices` whose language matches `requested`."""
    for v in voices:
        if matches_language(v.language, requested):
            return v
    return None
