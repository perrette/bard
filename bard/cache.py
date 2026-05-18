import os
import re
import json
import logging
from itertools import groupby
from pathlib import Path

logger = logging.getLogger("bard")

HOME = os.environ.get('HOME', os.path.expanduser('~'))
XDG_CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.join(HOME, '.cache'))
CACHE_DIR = os.path.join(XDG_CACHE_HOME, 'bard')


def parse_file(file):
    """
    Parse timestamp and index from filename.
    Supports:
      chunk_<ts>_<index>.<ext>                      (old)
      chunk_<ts>_<backend>_<index>.<ext>            (intermediate)
      chunk_<ts>_<backend>_<voice>_<index>.<ext>    (current)
      merged_<ts>.<ext>                             (merged, no index)
    Returns (None, 0) on no match.
    """
    stem = Path(file).stem
    prefix_match = re.match(r'^(chunk|merged)_(.*)', stem)
    if not prefix_match:
        return (None, 0)

    prefix, rest = prefix_match.groups()
    ts_match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{6}\.\d{6})(.*)', rest)
    if not ts_match:
        return (None, 0)

    date, remainder = ts_match.groups()

    idx_match = re.search(r'_(\d+)$', remainder)
    if idx_match:
        return date, int(idx_match.group(1))

    if prefix == 'merged':
        return date, -1

    return (None, 0)


def get_audio_files_from_cache(index=-1, cache_dir=None):
    """
    Return the files of the index-th batch in the cache, oldest-first.
    A batch is grouped by timestamp; if a merged_<timestamp>.<ext> file
    exists for a batch, only that file is returned (chunks are considered
    superseded).
    """
    cache_path = Path(cache_dir or CACHE_DIR)
    all_files = [
        f for f in list(cache_path.glob("chunk_*.*")) + list(cache_path.glob("merged_*.*"))
        if f.suffix != '.json'
    ]

    sorted_files = sorted(all_files, key=parse_file)

    batches = []
    for _, group in groupby(sorted_files, key=lambda f: parse_file(f)[0]):
        files = list(group)
        merged = [f for f in files if f.name.startswith("merged_")]
        batches.append(merged if merged else files)

    if not batches:
        logger.error("No files found in the cache directory")
        return []

    try:
        return batches[index]
    except IndexError:
        logger.error("Invalid index: %s. Return last played file.", index)
        return batches[-1]


def is_parent_directory(potential_parent, file_path):
    potential_parent = Path(potential_parent).resolve()
    file_path = Path(file_path).resolve()
    return potential_parent in file_path.parents


def get_resume_files(cache_dir=None, index=-1):
    """
    Return files for --resume: prefer the most recent manifest, fall back to cache scan.
    """
    cache_path = Path(cache_dir or CACHE_DIR)
    manifests = sorted(cache_path.glob("manifest_*_*.json"), key=lambda f: f.name)
    if manifests:
        manifest_file = manifests[index]
        try:
            data = json.loads(manifest_file.read_text())
            files = [Path(f) for f in data.get('files', [])]
            existing = [f for f in files if f.exists()]
            if existing:
                return existing
        except Exception as e:
            logger.warning("Could not read manifest %s: %s", manifest_file, e)
    return get_audio_files_from_cache(index, cache_dir)
