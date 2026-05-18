from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Iterator


@dataclass(frozen=True)
class Voice:
    id: str
    language: str | None = None
    gender: str | None = None
    display: str | None = None

    def __str__(self) -> str:
        return self.id


class TTSBackend(ABC):
    name: str
    default_voice: str
    default_model: str | None
    output_format: str
    sample_rate: int | None
    supports_streaming: bool = False
    is_local: ClassVar[bool] = False
    install_hint: ClassVar[str | None] = None

    @abstractmethod
    def synthesize(self, text: str, out_path: Path) -> Path:
        ...

    @abstractmethod
    def list_voices(self) -> list[str]:
        ...

    def list_voices_meta(self) -> list["Voice"]:
        return [Voice(id=v) for v in self.list_voices()]

    def list_models(self) -> list[str]:
        return [self.default_model] if self.default_model else []

    def synthesize_stream(self, text: str) -> Iterator[bytes]:
        raise NotImplementedError
