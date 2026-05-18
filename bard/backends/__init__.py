from bard.backends.base import TTSBackend

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

__all__ = ["TTSBackend", "BACKENDS", "get_backend", "OpenAIBackend", "KokoroBackend"]
