import os
from pathlib import Path
from typing import Iterator

from bard.backends.base import TTSBackend, Voice


_DEFAULT_VOICES = {
    "Aria": "9BWtsMINqrJLrRacOk9x",
    "Roger": "CwhRBWXzGAHq8TQ4Fs17",
    "Sarah": "EXAVITQu4vr4xnSDxMaL",
    "Laura": "FGY2WhTYpPnrIDTdsKH5",
    "George": "JBFqnCBsd6RMkjVDRZzb",
    "Charlie": "IKne3meq5aSn9XLyUdCD",
    "Bill": "pqHfZKP75CvOlQylNhV4",
    "Brian": "nPczCjzI2devNBz1zQrb",
}

_FALLBACK_VOICES_META: list[Voice] = [
    Voice(id="Aria", language="en", gender="female", display="Aria"),
    Voice(id="Sarah", language="en", gender="female", display="Sarah"),
    Voice(id="Laura", language="en", gender="female", display="Laura"),
    Voice(id="Roger", language="en", gender="male", display="Roger"),
    Voice(id="George", language="en", gender="male", display="George"),
    Voice(id="Charlie", language="en", gender="male", display="Charlie"),
    Voice(id="Bill", language="en", gender="male", display="Bill"),
    Voice(id="Brian", language="en", gender="male", display="Brian"),
]


_FALLBACK_MODELS = ["eleven_turbo_v2_5", "eleven_flash_v2_5", "eleven_multilingual_v2", "eleven_v3"]


class ElevenLabsBackend(TTSBackend):
    name = "elevenlabs"
    default_voice = "Aria"
    default_model = "eleven_turbo_v2_5"
    output_format = "mp3"
    sample_rate = None
    supports_streaming = True
    is_local = False

    def __init__(self, api_key=None, voice=None, model=None, output_format=None, **kwargs):
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError as e:
            raise ImportError("pip install bard-cli[elevenlabs]") from e

        api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY is not set. Get one at https://elevenlabs.io "
                "and export it as ELEVENLABS_API_KEY."
            )

        self.client = ElevenLabs(api_key=api_key)
        self.voice = voice or self.default_voice
        self.model = model or self.default_model
        if output_format:
            self.output_format = output_format
        self._voice_cache: list[str] | None = None
        self._model_cache: list[str] | None = None

    def _resolve_voice_id(self, voice: str) -> str:
        return _DEFAULT_VOICES.get(voice, voice)

    def _stream(self, text: str) -> Iterator[bytes]:
        audio_iter = self.client.text_to_speech.convert(
            text=text,
            voice_id=self._resolve_voice_id(self.voice),
            model_id=self.model,
            output_format="mp3_44100_128",
        )
        for chunk in audio_iter:
            if chunk:
                yield chunk

    def synthesize(self, text: str, out_path: Path) -> Path:
        with open(out_path, "wb") as f:
            for chunk in self._stream(text):
                f.write(chunk)
        return out_path

    def synthesize_stream(self, text: str) -> Iterator[bytes]:
        yield from self._stream(text)

    def list_voices(self) -> list[str]:
        if self._voice_cache is not None:
            return list(self._voice_cache)
        from bard.backends import diskcache
        cached = diskcache.load("elevenlabs", "voices", diskcache.DEFAULT_TTL_SECONDS)
        if cached is not None:
            self._voice_cache = cached
            return list(cached)
        try:
            response = self.client.voices.get_all()
            voices = [v.name for v in response.voices]
            self._voice_cache = voices
            diskcache.save("elevenlabs", "voices", voices)
            return list(voices)
        except Exception:
            return list(_DEFAULT_VOICES.keys())

    def list_models(self) -> list[str]:
        if self._model_cache is not None:
            return list(self._model_cache)
        from bard.backends import diskcache
        cached = diskcache.load("elevenlabs", "models", diskcache.DEFAULT_TTL_SECONDS)
        if cached is not None:
            self._model_cache = cached
            return list(cached)
        try:
            ids = [m.model_id for m in self.client.models.list() if m.can_do_text_to_speech]
            result = ids or list(_FALLBACK_MODELS)
            self._model_cache = result
            diskcache.save("elevenlabs", "models", result)
            return list(result)
        except Exception:
            return list(_FALLBACK_MODELS)

    def list_voices_meta(self) -> list[Voice]:
        cached = getattr(self, "_meta_cache", None)
        if cached is not None:
            return cached
        from bard.backends import diskcache
        disk = diskcache.load("elevenlabs", "voices_meta", diskcache.DEFAULT_TTL_SECONDS)
        if disk is not None:
            result = [Voice(**v) for v in disk]
            self._meta_cache = result
            return result
        try:
            response = self.client.voices.get_all()
            result = []
            for v in response.voices:
                labels = getattr(v, "labels", {}) or {}
                language = labels.get("language") or labels.get("accent")
                gender = labels.get("gender")
                result.append(Voice(id=v.name, language=language, gender=gender, display=v.name))
            self._meta_cache = result
            diskcache.save("elevenlabs", "voices_meta", [
                {"id": v.id, "language": v.language, "gender": v.gender, "display": v.display}
                for v in result
            ])
            return result
        except Exception:
            return list(_FALLBACK_VOICES_META)
