import os
import re
from pathlib import Path
import logging
import shutil
from itertools import groupby

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bard")

HOME = os.environ.get('HOME', os.path.expanduser('~'))
XDG_CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.join(HOME, '.cache'))
CACHE_DIR = os.path.join(XDG_CACHE_HOME, 'bard')

def clean_cache():
    logger.info(f"Cleaning cache directory: {CACHE_DIR}")
    shutil.rmtree(CACHE_DIR)

def get_cache_path(filename):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, filename)

def is_running_in_termux():
    return os.environ.get('PREFIX') == '/data/data/com.termux/files/usr'


def parse_file(file):
    """
    Parse the timestamp and index from the file name.
    e.g. chunk_2025-02-22T010457.819224_1.mp3  -> (date, 1)
         merged_2025-02-22T010457.819224.mp3   -> (date, -1)
    """
    match = re.search(r'(?:chunk|merged)_(\d{4}-\d{2}-\d{2}T\d{6}\.\d{6})(?:_(\d+))?\..', str(file))
    if match:
        date, chunk = match.groups()
        return date, int(chunk) if chunk is not None else -1
    else:
        return (None, 0) # no match


def get_audio_files_from_cache(index=-1):
    """
    Return the files of the index-th batch in the cache, oldest-first.
    A batch is grouped by timestamp; if a merged_<timestamp>.<ext> file
    exists for a batch, only that file is returned (chunks are considered
    superseded).
    """
    all_files = (list(Path(CACHE_DIR).glob("chunk_*.mp3"))
                 + list(Path(CACHE_DIR).glob("merged_*.mp3")))

    sorted_files = sorted(all_files, key=parse_file)  # merged (idx=-1) sorts before chunks within a batch

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
        logger.error(f"Invalid index: {index}. Return last played file.")
        return batches[-1]



def is_parent_directory(potential_parent, file_path):
    potential_parent = Path(potential_parent).resolve()
    file_path = Path(file_path).resolve()

    # Check if the potential parent is in the list of parent directories
    return potential_parent in file_path.parents
