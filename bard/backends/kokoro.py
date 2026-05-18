import os
from pathlib import Path

from bard.backends.base import TTSBackend, Voice


_DEFAULT_MODEL_PATH = Path.home() / ".cache" / "bard" / "kokoro" / "kokoro-v0_19.onnx"
_DEFAULT_VOICES_PATH = Path.home() / ".cache" / "bard" / "kokoro" / "voices.bin"

_VOICES = [
    "af",
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_michael",
    "bf_emma",
    "bf_isabella",
    "bm_george",
    "bm_lewis",
]


class KokoroBackend(TTSBackend):
    name = "kokoro"
    default_voice = "af_sky"
    default_model = None
    output_format = "wav"
    sample_rate = 24000
    supports_streaming = False
    is_local = True

    def __init__(self, voice=None, model=None, model_path=None, voices_path=None, lang="en-us", speed=1.0, **kwargs):
        try:
            from kokoro_onnx import Kokoro  # noqa: F401
            import onnxruntime  # noqa: F401
        except ImportError as e:
            raise ImportError("pip install bard-cli[kokoro]") from e

        self.voice = voice or self.default_voice
        self.model = model
        self.lang = lang
        self.speed = speed

        model_path = Path(model_path or os.environ.get("BARD_KOKORO_MODEL_PATH") or _DEFAULT_MODEL_PATH)
        voices_path = Path(voices_path or os.environ.get("BARD_KOKORO_VOICES_PATH") or _DEFAULT_VOICES_PATH)

        if not model_path.exists():
            raise FileNotFoundError(
                f"Kokoro model not found at {model_path}. "
                "Set BARD_KOKORO_MODEL_PATH or place the file at the default location."
            )
        if not voices_path.exists():
            raise FileNotFoundError(
                f"Kokoro voices file not found at {voices_path}. "
                "Set BARD_KOKORO_VOICES_PATH or place the file at the default location."
            )

        self._kokoro = Kokoro(str(model_path), str(voices_path))

    def synthesize(self, text: str, out_path: Path) -> Path:
        import soundfile as sf

        samples, sample_rate = self._kokoro.create(
            text, voice=self.voice, speed=self.speed, lang=self.lang
        )
        sf.write(str(out_path), samples, sample_rate)
        return out_path

    def list_voices(self) -> list[str]:
        return list(_VOICES)

    def list_voices_meta(self) -> list[Voice]:
        _LANG = {"a": "en-US", "b": "en-GB"}
        _GENDER = {"f": "female", "m": "male"}
        result = []
        for vid in _VOICES:
            parts = vid.split("_", 1)
            if len(parts) == 2 and len(parts[0]) == 2:
                language = _LANG.get(parts[0][0])
                gender = _GENDER.get(parts[0][1])
            else:
                language = "en"
                gender = None
            result.append(Voice(id=vid, language=language, gender=gender))
        return result
