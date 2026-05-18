from pathlib import Path

from bard.backends.base import TTSBackend, Voice


class OpenAIBackend(TTSBackend):
    name = "openai"
    default_voice = "alloy"
    default_model = "tts-1"
    output_format = "mp3"
    sample_rate = None
    supports_streaming = False

    _VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def __init__(self, api_key=None, voice=None, model=None, max_length=None, output_format="mp3"):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("pip install bard-cli[openai]") from e
        self.client = OpenAI(api_key=api_key)
        self.model = model or "tts-1"
        self.voice = voice or "alloy"
        self.output_format = output_format
        self.max_length = max_length or 4096

    def synthesize(self, text: str, out_path: Path) -> Path:
        response = self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format=self.output_format,
        )
        response.stream_to_file(str(out_path))
        return out_path

    def list_voices(self) -> list[str]:
        return list(self._VOICES)

    _VOICE_META = {
        "alloy":   Voice(id="alloy",   language="en", gender=None),
        "echo":    Voice(id="echo",    language="en", gender="male"),
        "fable":   Voice(id="fable",   language="en", gender="male"),
        "onyx":    Voice(id="onyx",    language="en", gender="male"),
        "nova":    Voice(id="nova",    language="en", gender="female"),
        "shimmer": Voice(id="shimmer", language="en", gender="female"),
    }

    def list_voices_meta(self) -> list[Voice]:
        return [self._VOICE_META[v] for v in self._VOICES]
