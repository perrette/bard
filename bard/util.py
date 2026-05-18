import os
import logging
import shutil

from bard.cache import parse_file, get_audio_files_from_cache, is_parent_directory, CACHE_DIR  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bard")

HOME = os.environ.get('HOME', os.path.expanduser('~'))
XDG_CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.join(HOME, '.cache'))


def clean_cache():
    logger.info(f"Cleaning cache directory: {CACHE_DIR}")
    shutil.rmtree(CACHE_DIR)

def get_cache_path(filename):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, filename)

def is_running_in_termux():
    return os.environ.get('PREFIX') == '/data/data/com.termux/files/usr'
