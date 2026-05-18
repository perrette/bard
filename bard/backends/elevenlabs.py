import os
from pathlib import Path
from typing import Iterator

from bard.backends.base import TTSBackend, Voice


_DEFAULT_VOICES = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Bella": "EXAVITQu4vr4xnSDxMaL",
    "Domi": "AZnzlk1XvdvUeBnXmlld",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Sam": "yoZ06aMxZJJ28mfd3POQ",
}

_FALLBACK_VOICES_META: list[Voice] = [
    Voice(id="Rachel", language="en", gender="female", display="Rachel"),
    Voice(id="Bella", language="en", gender="female", display="Bella"),
    Voice(id="Domi", language="en", gender="female", display="Domi"),
    Voice(id="Elli", language="en", gender="female", display="Elli"),
    Voice(id="Adam", language="en", gender="male", display="Adam"),
    Voice(id="Antoni", language="en", gender="male", display="Antoni"),
    Voice(id="Josh", language="en", gender="male", display="Josh"),
    Voice(id="Sam", language="en", gender="male", display="Sam"),
]


class ElevenLabsBackend(TTSBackend):
    name = "elevenlabs"
    default_voice = "Rachel"
    default_model = "eleven_turbo_v2_5"
    output_format = "mp3"
    sample_rate = None
    supports_streaming = True

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
        try:
            response = self.client.voices.get_all()
            voices = [v.name for v in response.voices]
            self._voice_cache = voices
            return list(voices)
        except Exception:
            return list(_DEFAULT_VOICES.keys())

    def list_voices_meta(self) -> list[Voice]:
        cached = getattr(self, "_meta_cache", None)
        if cached is not None:
            return cached
        try:
            response = self.client.voices.get_all()
            result = []
            for v in response.voices:
                labels = getattr(v, "labels", {}) or {}
                language = labels.get("language") or labels.get("accent")
                gender = labels.get("gender")
                result.append(Voice(id=v.name, language=language, gender=gender, display=v.name))
            self._meta_cache = result
            return result
        except Exception:
            return list(_FALLBACK_VOICES_META)
