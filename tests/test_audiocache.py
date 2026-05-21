import os
import time
from pathlib import Path

import pytest

from bard import audiocache
from bard.chunking import _synthesize_with_cache


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Redirect the audio cache to a temp dir for each test."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    return tmp_path / "bard" / "audio_cache"


class StubBackend:
    name = "openai"
    default_voice = "alloy"
    default_model = "gpt-4o-mini-tts"
    output_format = "mp3"
    is_local = False

    def __init__(self, voice="nova", model="tts-1", output_format="mp3"):
        self.voice = voice
        self.model = model
        self.output_format = output_format
        self.calls = 0

    def synthesize(self, text, out_path):
        self.calls += 1
        Path(out_path).write_bytes(f"AUDIO[{self.voice}|{self.model}|{text}]".encode())
        return out_path


# ---------------------------------------------------------------------------
# request_fingerprint
# ---------------------------------------------------------------------------

def test_fingerprint_is_deterministic():
    b = StubBackend()
    assert audiocache.request_fingerprint(b, "hello") == audiocache.request_fingerprint(b, "hello")


def test_fingerprint_changes_with_text():
    b = StubBackend()
    assert audiocache.request_fingerprint(b, "hello") != audiocache.request_fingerprint(b, "world")


def test_fingerprint_changes_with_voice():
    a = StubBackend(voice="nova")
    b = StubBackend(voice="alloy")
    assert audiocache.request_fingerprint(a, "x") != audiocache.request_fingerprint(b, "x")


def test_fingerprint_changes_with_model():
    a = StubBackend(model="tts-1")
    b = StubBackend(model="tts-1-hd")
    assert audiocache.request_fingerprint(a, "x") != audiocache.request_fingerprint(b, "x")


def test_fingerprint_changes_with_output_format():
    a = StubBackend(output_format="mp3")
    b = StubBackend(output_format="opus")
    assert audiocache.request_fingerprint(a, "x") != audiocache.request_fingerprint(b, "x")


def test_fingerprint_changes_with_backend_name():
    a = StubBackend()
    b = StubBackend()
    b.name = "elevenlabs"
    assert audiocache.request_fingerprint(a, "x") != audiocache.request_fingerprint(b, "x")


def test_fingerprint_includes_backend_extras():
    a = StubBackend()
    b = StubBackend()
    a.cache_fingerprint_extras = lambda: {"speed": 1.0}
    b.cache_fingerprint_extras = lambda: {"speed": 1.25}
    assert audiocache.request_fingerprint(a, "x") != audiocache.request_fingerprint(b, "x")


def test_fingerprint_extras_are_order_independent():
    a = StubBackend()
    b = StubBackend()
    a.cache_fingerprint_extras = lambda: {"speed": 1.0, "style": "calm"}
    b.cache_fingerprint_extras = lambda: {"style": "calm", "speed": 1.0}
    assert audiocache.request_fingerprint(a, "x") == audiocache.request_fingerprint(b, "x")


def test_fingerprint_uses_backend_defaults_when_attrs_missing():
    class Bare:
        name = "openai"
        default_voice = "alloy"
        default_model = "gpt-4o-mini-tts"
        output_format = "mp3"

    # No instance attrs for voice/model — should fall back to defaults
    # and still produce a stable, sensible hash.
    h = audiocache.request_fingerprint(Bare(), "hello")
    assert isinstance(h, str) and len(h) == 64


# ---------------------------------------------------------------------------
# try_load / store
# ---------------------------------------------------------------------------

def test_try_load_miss_returns_false(isolated_cache, tmp_path):
    out = tmp_path / "out.mp3"
    assert audiocache.try_load("openai", "deadbeef", "mp3", out) is False
    assert not out.exists()


def test_store_then_load_round_trip(isolated_cache, tmp_path):
    src = tmp_path / "src.mp3"
    src.write_bytes(b"audio-bytes")
    audiocache.store("openai", "abc123", "mp3", src)

    out = tmp_path / "out.mp3"
    assert audiocache.try_load("openai", "abc123", "mp3", out) is True
    assert out.read_bytes() == b"audio-bytes"


def test_try_load_treats_stale_entry_as_miss(isolated_cache, tmp_path):
    src = tmp_path / "src.mp3"
    src.write_bytes(b"old")
    audiocache.store("openai", "stale", "mp3", src)

    # Back-date the cached file by 8 days; default TTL is 7d.
    cached = isolated_cache / "openai" / "stale.mp3"
    old = time.time() - 8 * 24 * 3600
    os.utime(cached, (old, old))

    out = tmp_path / "out.mp3"
    assert audiocache.try_load("openai", "stale", "mp3", out, ttl_seconds=7 * 24 * 3600) is False
    assert not out.exists()


def test_try_load_refreshes_mtime_on_hit(isolated_cache, tmp_path):
    src = tmp_path / "src.mp3"
    src.write_bytes(b"x")
    audiocache.store("openai", "slide", "mp3", src)

    cached = isolated_cache / "openai" / "slide.mp3"
    # Back-date but keep within TTL.
    old = time.time() - 3600
    os.utime(cached, (old, old))

    out = tmp_path / "out.mp3"
    assert audiocache.try_load("openai", "slide", "mp3", out) is True
    assert cached.stat().st_mtime > old


def test_clear_all_removes_cache(isolated_cache, tmp_path):
    src = tmp_path / "src.mp3"
    src.write_bytes(b"x")
    audiocache.store("openai", "k", "mp3", src)
    assert (isolated_cache / "openai" / "k.mp3").exists()

    audiocache.clear_all()
    assert not isolated_cache.exists()


def test_clear_all_is_safe_when_cache_absent(isolated_cache):
    # Nothing was ever stored — must not raise.
    audiocache.clear_all()


# ---------------------------------------------------------------------------
# _synthesize_with_cache integration
# ---------------------------------------------------------------------------

def test_remote_backend_caches_repeated_text(isolated_cache, tmp_path):
    b = StubBackend()
    out1 = tmp_path / "a.mp3"
    out2 = tmp_path / "b.mp3"

    _synthesize_with_cache(b, "hello", out1)
    _synthesize_with_cache(b, "hello", out2)

    assert b.calls == 1
    assert out1.read_bytes() == out2.read_bytes()


def test_remote_backend_different_text_misses(isolated_cache, tmp_path):
    b = StubBackend()
    _synthesize_with_cache(b, "hello", tmp_path / "a.mp3")
    _synthesize_with_cache(b, "world", tmp_path / "b.mp3")
    assert b.calls == 2


@pytest.mark.parametrize("attr,new_value", [
    ("voice", "shimmer"),
    ("model", "tts-1-hd"),
    ("output_format", "opus"),
])
def test_remote_backend_setting_change_invalidates_cache(isolated_cache, tmp_path, attr, new_value):
    b = StubBackend()
    _synthesize_with_cache(b, "hello", tmp_path / "a.mp3")
    setattr(b, attr, new_value)
    _synthesize_with_cache(b, "hello", tmp_path / "b.mp3")
    assert b.calls == 2


def test_local_backend_bypasses_cache(isolated_cache, tmp_path):
    class LocalStub(StubBackend):
        is_local = True

    b = LocalStub()
    _synthesize_with_cache(b, "hello", tmp_path / "a.mp3")
    _synthesize_with_cache(b, "hello", tmp_path / "b.mp3")

    assert b.calls == 2
    # And nothing was written to the audio cache directory.
    assert not isolated_cache.exists() or not any(isolated_cache.rglob("*.mp3"))


def test_cache_persists_across_backend_instances(isolated_cache, tmp_path):
    b1 = StubBackend()
    _synthesize_with_cache(b1, "hello", tmp_path / "a.mp3")
    assert b1.calls == 1

    # A fresh backend instance with the same settings should hit the on-disk cache.
    b2 = StubBackend()
    _synthesize_with_cache(b2, "hello", tmp_path / "b.mp3")
    assert b2.calls == 0
