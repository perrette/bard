from bard.backends.base import TTSBackend

BACKENDS: dict[str, type[TTSBackend]] = {}


def get_backend(name: str, **kwargs) -> TTSBackend:
    if name not in BACKENDS:
        raise KeyError(name)
    return BACKENDS[name](**kwargs)


__all__ = ["TTSBackend", "BACKENDS", "get_backend"]
