import os
import wave
from pathlib import Path

from bard.backends.base import TTSBackend


_DEFAULT_MODEL_PATH = Path.home() / ".cache" / "bard" / "piper" / "en_US-amy-medium.onnx"


class PiperBackend(TTSBackend):
    name = "piper"
    default_voice = "en_US-amy-medium"
    default_model = None
    output_format = "wav"
    sample_rate: int | None = None
    supports_streaming = False

    def __init__(self, voice=None, model=None, model_path=None, **kwargs):
        try:
            from piper.voice import PiperVoice
        except ImportError as e:
            raise ImportError("pip install bard-cli[piper]") from e

        model_path = Path(model_path or os.environ.get("BARD_PIPER_MODEL") or _DEFAULT_MODEL_PATH)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Piper model not found at {model_path}. "
                "Set BARD_PIPER_MODEL or place the .onnx file at the default location."
            )

        self._voice = PiperVoice.load(str(model_path))
        self._model_path = model_path
        self.sample_rate = self._voice.config.sample_rate
        self.voice = voice or model_path.stem
        self.model = model

    def synthesize(self, text: str, out_path: Path) -> Path:
        with wave.open(str(out_path), "wb") as wav_file:
            self._voice.synthesize(text, wav_file)
        return out_path

    def list_voices(self) -> list[str]:
        return [self._model_path.stem]
