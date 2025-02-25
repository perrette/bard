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
    Parse the timestamp and index from the file name
    e.g. chunk_2025-02-22T010457.819224_1.mp3
    """
    match = re.search(r'chunk_(\d{4}-\d{2}-\d{2}T\d{6}\.\d{6})_(\d+)\..', str(file))
    if match:
        date, chunk = match.groups()
        return date, int(chunk)
    else:
        return (None, 0) # no match


def get_audio_files_from_cache(index=-1):
    """
    scan the cache directory for the most recent files
    use the pattern f"chunk_{timestamp}_{i}.{self.output_format}"
    e.g. chunk_2025-02-22T010457.819224_1.mp3
    and keep only the latest timestamp
    sort them by index {i} which may occupy more than one digit
    """
    all_files = list(Path(CACHE_DIR).glob("chunk_*.mp3"))

    sorted_files_parsed = sorted(map((lambda x: (x, parse_file(x))), all_files), key=lambda x: x[1]) # (file, (date, index))
    files_by_chunks = [[file for file, ids in chunks] for k, chunks in groupby(sorted_files_parsed, key=lambda x: x[1][0])]

    if len(files_by_chunks) == 0:
        logger.error("No files found in the cache directory")
        return []

    try:
        return files_by_chunks[index]
    except IndexError:
        logger.error(f"Invalid index: {index}. Return last played file.")
        return files_by_chunks[-1]



def is_parent_directory(potential_parent, file_path):
    potential_parent = Path(potential_parent).resolve()
    file_path = Path(file_path).resolve()

    # Check if the potential parent is in the list of parent directories
    return potential_parent in file_path.parents
