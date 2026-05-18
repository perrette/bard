from pathlib import Path

from desktop_ai_core.providers import TTSBackend, Voice
from bard.backends.paths import resolve_model_path


_DEFAULT_MODEL_FILENAME = "kokoro-v1.0.onnx"
_DEFAULT_VOICES_FILENAME = "voices-v1.0.bin"

# Voice prefix -> (espeak lang code, ISO language tag, gender map by 2nd char).
# The first char of a voice ID is the language, the second is the gender.
_LANG_BY_PREFIX = {
    "a": ("en-us", "en-US"),
    "b": ("en-gb", "en-GB"),
    "j": ("ja", "ja"),
    "z": ("cmn", "zh"),
    "e": ("es", "es"),
    "f": ("fr-fr", "fr"),
    "h": ("hi", "hi"),
    "i": ("it", "it"),
    "p": ("pt-br", "pt-BR"),
}

_VOICES = [
    # American English
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa",
    # British English
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    # Japanese
    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo",
    # Mandarin Chinese
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
    # Spanish
    "ef_dora", "em_alex", "em_santa",
    # French
    "ff_siwis",
    # Hindi
    "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
    # Italian
    "if_sara", "im_nicola",
    # Brazilian Portuguese
    "pf_dora", "pm_alex", "pm_santa",
]


_KOKORO_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"


class KokoroBackend(TTSBackend):
    name = "kokoro"
    default_voice = "af_heart"
    default_model = None
    output_format = "wav"
    sample_rate = 24000
    supports_streaming = False
    is_local = True
    install_hint = (
        "mkdir -p ~/.local/share/kokoro && "
        f"curl -L -o ~/.local/share/kokoro/{_DEFAULT_MODEL_FILENAME} {_KOKORO_RELEASE}/{_DEFAULT_MODEL_FILENAME} && "
        f"curl -L -o ~/.local/share/kokoro/{_DEFAULT_VOICES_FILENAME} {_KOKORO_RELEASE}/{_DEFAULT_VOICES_FILENAME}"
    )

    def __init__(self, voice=None, model=None, model_path=None, voices_path=None, lang=None, speed=1.0, **kwargs):
        try:
            from kokoro_onnx import Kokoro  # noqa: F401
            import onnxruntime  # noqa: F401
        except ImportError as e:
            raise ImportError("pip install bard-cli[kokoro]") from e

        self.voice = voice or self.default_voice
        self.model = model
        self.lang = lang or _lang_for_voice(self.voice)
        self.speed = speed

        model_path = resolve_model_path("BARD_KOKORO_MODEL_PATH", "kokoro", _DEFAULT_MODEL_FILENAME, model_path)
        voices_path = resolve_model_path("BARD_KOKORO_VOICES_PATH", "kokoro", _DEFAULT_VOICES_FILENAME, voices_path)

        if not model_path.exists():
            raise FileNotFoundError(
                f"Kokoro model not found at {model_path}.\n"
                f"To install: {self.install_hint}"
            )
        if not voices_path.exists():
            raise FileNotFoundError(
                f"Kokoro voices file not found at {voices_path}.\n"
                f"To install: {self.install_hint}"
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
        _GENDER = {"f": "female", "m": "male"}
        result = []
        for vid in _VOICES:
            parts = vid.split("_", 1)
            if len(parts) == 2 and len(parts[0]) == 2:
                lang_entry = _LANG_BY_PREFIX.get(parts[0][0])
                language = lang_entry[1] if lang_entry else None
                gender = _GENDER.get(parts[0][1])
            else:
                language = "en"
                gender = None
            result.append(Voice(id=vid, language=language, gender=gender))
        return result


def _lang_for_voice(voice_id: str) -> str:
    """Derive the espeak language code for a Kokoro v1.0 voice ID."""
    if len(voice_id) >= 1:
        entry = _LANG_BY_PREFIX.get(voice_id[0])
        if entry is not None:
            return entry[0]
    return "en-us"
