import re
import wave
from pathlib import Path

from desktop_ai_core.providers import TTSBackend, Voice
from bard.backends.paths import resolve_model_path


_DEFAULT_VOICE_FILENAME = "en_US-amy-medium.onnx"

_STEM_RE = re.compile(r"^([a-z]{2,3})(?:_([A-Z]{2,3}))?-(.+)-([^-]+)$")


class PiperBackend(TTSBackend):
    name = "piper"
    default_voice = "en_US-amy-medium"
    default_model = None
    output_format = "wav"
    sample_rate: int | None = None
    supports_streaming = False
    is_local = True
    install_hint = "python -m piper.download_voices en_US-amy-medium --data-dir ~/.local/share/piper"

    def __init__(self, voice=None, model=None, model_path=None, **kwargs):
        try:
            from piper.voice import PiperVoice
        except ImportError as e:
            raise ImportError("pip install bard-cli[piper]") from e

        model_path = resolve_model_path("BARD_PIPER_MODEL", "piper", _DEFAULT_VOICE_FILENAME, model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Piper model not found at {model_path}.\n"
                f"To install: {self.install_hint}"
            )

        self._voice = PiperVoice.load(str(model_path))
        self._model_path = model_path
        self.sample_rate = self._voice.config.sample_rate
        self._voice_id = model_path.stem
        if voice:
            self.voice = voice
        self.model = model

    @property
    def voice(self) -> str:
        return self._voice_id

    @voice.setter
    def voice(self, stem: str) -> None:
        if stem == self._voice_id:
            return
        parent = self._model_path.parent
        candidate = parent / f"{stem}.onnx"
        if not candidate.exists():
            raise ValueError(f"Unknown Piper voice {stem!r}; not found in {parent}")
        from piper.voice import PiperVoice
        self._voice = PiperVoice.load(str(candidate))
        self._model_path = candidate
        self.sample_rate = self._voice.config.sample_rate
        self._voice_id = stem

    def synthesize(self, text: str, out_path: Path) -> Path:
        with wave.open(str(out_path), "wb") as wav_file:
            self._voice.synthesize_wav(text, wav_file)
        return out_path

    def list_voices(self) -> list[str]:
        current_stem = self._model_path.stem
        parent = self._model_path.parent
        if not parent.exists():
            return [current_stem]
        stems = sorted(p.stem for p in parent.glob("*.onnx"))
        if not stems:
            return [current_stem]
        others = [s for s in stems if s != current_stem]
        return [current_stem] + others

    def list_voices_meta(self) -> list[Voice]:
        out: list[Voice] = []
        for stem in self.list_voices():
            m = _STEM_RE.match(stem)
            if m:
                lang, country, name, quality = m.groups()
                language = f"{lang}-{country}" if country else lang
                display = f"{name} ({language}, {quality})"
                out.append(Voice(id=stem, language=language, gender=None, display=display))
            else:
                out.append(Voice(id=stem))
        return out
