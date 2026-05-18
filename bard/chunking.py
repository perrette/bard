import re
import json
import hashlib
import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterator


def split_text_into_chunks(text: str, chunk_size: int = 500) -> list[str]:
    # Regular expression to split text at punctuation marks
    punctuation_marks = re.compile(r'([.!?])\s*')

    # Split the text into sentences
    sentences = punctuation_marks.split(text.strip())

    # Combine sentences into chunks of up to chunk_size characters
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

        if current_length + sentence_length > chunk_size and current_chunk:
            chunks.append("".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(sentence)
        current_chunk.append(punctuation)
        current_length += sentence_length

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks


def render_chunks(backend, text: str, chunk_size: int, cache_dir) -> Iterator[Path]:
    # Streaming-capable backends still produce one complete file per chunk here;
    # intra-chunk byte streaming (synthesize_stream) is a separate code path.
    chunks = split_text_into_chunks(text, chunk_size=chunk_size)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat().replace(':', '')
    voice = getattr(backend, 'voice', backend.default_voice)
    model = getattr(backend, 'model', backend.default_model)
    out_paths = [
        cache_dir / f"chunk_{timestamp}_{backend.name}_{voice}_{i}.{backend.output_format}"
        for i in range(len(chunks))
    ]
    completed = []
    try:
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(backend.synthesize, chunk, out_path)
                for chunk, out_path in zip(chunks, out_paths)
            ]
            for future in futures:
                path = future.result()
                completed.append(path)
                yield path
    finally:
        if completed:
            manifest = {
                'backend': backend.name,
                'voice': voice,
                'model': model,
                'chunk_size': chunk_size,
                'text_hash': hashlib.md5(text.encode()).hexdigest(),
                'files': [str(p) for p in completed],
            }
            manifest_path = cache_dir / f"manifest_{timestamp}_{backend.name}_{voice}.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))
