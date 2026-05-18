import importlib.util
import os

from desktop_ai_core.providers import TTSBackend, Voice
from desktop_ai_core.providers.registry import (
    _TTS_REGISTRY,
    available_tts,
    get_tts,
    probe_tts,
    register_tts,
)
from bard.backends.paths import resolve_model_path

BACKENDS: dict[str, type[TTSBackend]] = _TTS_REGISTRY


def get_backend(name: str, **kwargs) -> TTSBackend:
    return get_tts(name, **kwargs)


def available_backends() -> list[str]:
    return available_tts()


def probe_backend(name: str) -> tuple[bool, str | None]:
    return probe_tts(name)


def _probe_openai() -> tuple[bool, str | None]:
    if importlib.util.find_spec("openai") is None:
        return False, "openai SDK not installed"
    if not os.environ.get("OPENAI_API_KEY"):
        return False, "OPENAI_API_KEY not set"
    return True, None


def _probe_elevenlabs() -> tuple[bool, str | None]:
    if importlib.util.find_spec("elevenlabs") is None:
        return False, "elevenlabs SDK not installed"
    if not os.environ.get("ELEVENLABS_API_KEY"):
        return False, "ELEVENLABS_API_KEY not set"
    return True, None


def _probe_kokoro() -> tuple[bool, str | None]:
    if importlib.util.find_spec("kokoro_onnx") is None:
        return False, "kokoro_onnx not installed"
    if importlib.util.find_spec("onnxruntime") is None:
        return False, "onnxruntime not installed"
    model_path = resolve_model_path("BARD_KOKORO_MODEL_PATH", "kokoro", "kokoro-v0_19.onnx")
    voices_path = resolve_model_path("BARD_KOKORO_VOICES_PATH", "kokoro", "voices.bin")
    if not model_path.exists():
        return False, f"model file not found: {model_path}"
    if not voices_path.exists():
        return False, f"voices file not found: {voices_path}"
    return True, None


def _probe_piper() -> tuple[bool, str | None]:
    if importlib.util.find_spec("piper") is None:
        return False, "piper not installed"
    model_path = resolve_model_path("BARD_PIPER_MODEL", "piper", "en_US-amy-medium.onnx")
    if not model_path.exists():
        return False, f"model file not found: {model_path}"
    return True, None


from bard.backends.openai import OpenAIBackend  # noqa: E402
register_tts("openai", OpenAIBackend, probe=_probe_openai)

from bard.backends.kokoro import KokoroBackend  # noqa: E402
register_tts("kokoro", KokoroBackend, probe=_probe_kokoro)

from bard.backends.elevenlabs import ElevenLabsBackend  # noqa: E402
register_tts("elevenlabs", ElevenLabsBackend, probe=_probe_elevenlabs)

from bard.backends.piper import PiperBackend  # noqa: E402
register_tts("piper", PiperBackend, probe=_probe_piper)

__all__ = [
    "BACKENDS", "get_backend",
    "available_backends", "probe_backend",
    "OpenAIBackend", "KokoroBackend", "ElevenLabsBackend", "PiperBackend",
]
