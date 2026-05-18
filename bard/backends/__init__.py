from bard.backends.base import TTSBackend, Voice

BACKENDS: dict[str, type[TTSBackend]] = {}


def get_backend(name: str, **kwargs) -> TTSBackend:
    if name not in BACKENDS:
        raise KeyError(name)
    return BACKENDS[name](**kwargs)


from bard.backends.openai import OpenAIBackend  # noqa: E402
BACKENDS["openai"] = OpenAIBackend
BACKENDS["openaiapi"] = OpenAIBackend

from bard.backends.kokoro import KokoroBackend  # noqa: E402
BACKENDS["kokoro"] = KokoroBackend

from bard.backends.elevenlabs import ElevenLabsBackend  # noqa: E402
BACKENDS["elevenlabs"] = ElevenLabsBackend

from bard.backends.piper import PiperBackend  # noqa: E402
BACKENDS["piper"] = PiperBackend

__all__ = ["TTSBackend", "Voice", "BACKENDS", "get_backend", "OpenAIBackend", "KokoroBackend", "ElevenLabsBackend", "PiperBackend"]
