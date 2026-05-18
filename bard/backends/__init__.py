import importlib.util
import os
from pathlib import Path

from bard.backends.base import TTSBackend, Voice

BACKENDS: dict[str, type[TTSBackend]] = {}


def get_backend(name: str, **kwargs) -> TTSBackend:
    if name not in BACKENDS:
        raise KeyError(name)
    return BACKENDS[name](**kwargs)


def available_backends() -> list[str]:
    return list(BACKENDS)


def probe_backend(name: str) -> tuple[bool, str | None]:
    if name not in BACKENDS:
        raise KeyError(name)

    if name == "openai":
        if importlib.util.find_spec("openai") is None:
            return False, "openai SDK not installed"
        if not os.environ.get("OPENAI_API_KEY"):
            return False, "OPENAI_API_KEY not set"
        return True, None

    if name == "elevenlabs":
        if importlib.util.find_spec("elevenlabs") is None:
            return False, "elevenlabs SDK not installed"
        if not os.environ.get("ELEVENLABS_API_KEY"):
            return False, "ELEVENLABS_API_KEY not set"
        return True, None

    if name == "kokoro":
        if importlib.util.find_spec("kokoro_onnx") is None:
            return False, "kokoro_onnx not installed"
        if importlib.util.find_spec("onnxruntime") is None:
            return False, "onnxruntime not installed"
        model_path = Path(
            os.environ.get("BARD_KOKORO_MODEL_PATH")
            or Path.home() / ".cache" / "bard" / "kokoro" / "kokoro-v0_19.onnx"
        )
        voices_path = Path(
            os.environ.get("BARD_KOKORO_VOICES_PATH")
            or Path.home() / ".cache" / "bard" / "kokoro" / "voices.bin"
        )
        if not model_path.exists():
            return False, f"model file not found: {model_path}"
        if not voices_path.exists():
            return False, f"voices file not found: {voices_path}"
        return True, None

    if name == "piper":
        if importlib.util.find_spec("piper") is None:
            return False, "piper not installed"
        model_path = Path(
            os.environ.get("BARD_PIPER_MODEL")
            or Path.home() / ".cache" / "bard" / "piper" / "en_US-amy-medium.onnx"
        )
        if not model_path.exists():
            return False, f"model file not found: {model_path}"
        return True, None

    return True, None


from bard.backends.openai import OpenAIBackend  # noqa: E402
BACKENDS["openai"] = OpenAIBackend

from bard.backends.kokoro import KokoroBackend  # noqa: E402
BACKENDS["kokoro"] = KokoroBackend

from bard.backends.elevenlabs import ElevenLabsBackend  # noqa: E402
BACKENDS["elevenlabs"] = ElevenLabsBackend

from bard.backends.piper import PiperBackend  # noqa: E402
BACKENDS["piper"] = PiperBackend

__all__ = [
    "TTSBackend", "Voice", "BACKENDS", "get_backend",
    "available_backends", "probe_backend",
    "OpenAIBackend", "KokoroBackend", "ElevenLabsBackend", "PiperBackend",
]
