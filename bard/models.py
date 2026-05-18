import os
import datetime
import tqdm
import time
from bard.util import logger, CACHE_DIR, clean_cache
from bard.chunking import split_text_into_chunks

class AbstractModel:
    pass

class OpenaiAPI(AbstractModel):
    def __init__(self, api_key=None, voice=None,
                 model=None, max_length=None, output_format="mp3"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
        )
        self.model = model or "tts-1"
        self.voice = voice or "alloy"
        self.output_format = output_format
        self.max_length = max_length or 4096
        self.is_downloading = False

    def text_to_audio_files(self, text):
        # Split the text into chunks of up to 4096 characters, ending at punctuation marks
        chunks = self.split_text_into_chunks(text, max_length=self.max_length)

        os.makedirs(CACHE_DIR, exist_ok=True)

        timestamp = f"{datetime.datetime.now().isoformat().replace(':', '')}"

        self.is_downloading = True

        try:
            for i, chunk in tqdm.tqdm(enumerate(chunks), total=len(chunks), desc="Generating audio"):
                output_file = os.path.join(CACHE_DIR, f"chunk_{timestamp}_{i}.{self.output_format}")
                self.generate_audio_file(chunk, output_file)
                yield output_file

        finally:
            self.is_downloading = False

    def wait(self):
        while self.is_downloading:
            time.sleep(0.1)

    def split_text_into_chunks(self, text, max_length):
        return split_text_into_chunks(text, chunk_size=max_length)

    def generate_audio_file(self, text, output_file):
        response = self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format=self.output_format,
        )

        response.stream_to_file(output_file)

        return output_file
