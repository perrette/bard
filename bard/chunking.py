import os
import re
import json
import shutil
import logging
import hashlib
import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterator

from bard import audiocache

logger = logging.getLogger(__name__)


def _max_concurrency() -> int:
    try:
        n = int(os.environ.get("BARD_MAX_CONCURRENCY", "4"))
    except ValueError:
        n = 4
    return max(1, n)


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


def _synthesize_with_cache(backend, text: str, out_path: Path) -> Path:
    """Wrap backend.synthesize with a content-addressed cache for remote backends."""
    if getattr(backend, "is_local", False):
        return backend.synthesize(text, out_path)
    key = audiocache.request_fingerprint(backend, text)
    ext = backend.output_format
    if audiocache.try_load(backend.name, key, ext, out_path):
        return out_path
    backend.synthesize(text, out_path)
    audiocache.store(backend.name, key, ext, out_path)
    return out_path


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
        with ThreadPoolExecutor(max_workers=_max_concurrency()) as executor:
            futures = [
                executor.submit(_synthesize_with_cache, backend, chunk, out_path)
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


def render_to_file(backend, text: str, chunk_size: int, output_path, cache_dir) -> str:
    """Render `text` through `backend` and write the concatenated audio to
    `output_path`. Returns the path written.

    Byte-concat: same-codec mp3 chunks (and most container formats this
    project produces -- opus/flac/aac/wav) tolerate stream concatenation.
    """
    output_path = str(output_path)
    sources = list(render_chunks(backend, text, chunk_size, cache_dir))
    ext = os.path.splitext(output_path)[1].lower()
    if ext and ext.lstrip(".") != backend.output_format.lower():
        logger.warning(
            f"--output-file extension {ext!r} differs from backend output_format "
            f"{backend.output_format!r}; the file will contain {backend.output_format} data."
        )
    out_dir = os.path.dirname(output_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "wb") as out:
        for f in sources:
            with open(f, "rb") as fp:
                shutil.copyfileobj(fp, out)
    return output_path
