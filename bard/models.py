import os
import re
import datetime
import tqdm
import shutil
import time
from bard.util import logger

HOME = os.environ.get('HOME', os.path.expanduser('~'))
XDG_CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.join(HOME, '.cache'))
CACHE_DIR = os.path.join(XDG_CACHE_HOME, 'bard')


def clean_cache():
    logger.info(f"Cleaning cache directory: {CACHE_DIR}")
    shutil.rmtree(CACHE_DIR)

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
        # Regular expression to split text at punctuation marks
        punctuation_marks = re.compile(r'([.!?])\s*')

        # Split the text into sentences
        sentences = punctuation_marks.split(text.strip())

        # Combine sentences into chunks of up to max_length characters
        chunks = []
        current_chunk = []
        current_length = 0

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_length = len(sentence) + len(punctuation)

            if current_length + sentence_length > max_length and current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = []
                current_length = 0

            current_chunk.append(sentence)
            current_chunk.append(punctuation)
            current_length += sentence_length

        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks

    def generate_audio_file(self, text, output_file):
        response = self.client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format=self.output_format,
        )

        response.stream_to_file(output_file)

        return output_file
