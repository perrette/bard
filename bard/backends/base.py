from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator


class TTSBackend(ABC):
    name: str
    default_voice: str
    default_model: str | None
    output_format: str
    sample_rate: int | None
    supports_streaming: bool = False

    @abstractmethod
    def synthesize(self, text: str, out_path: Path) -> Path:
        ...

    @abstractmethod
    def list_voices(self) -> list[str]:
        ...

    def synthesize_stream(self, text: str) -> Iterator[bytes]:
        raise NotImplementedError
