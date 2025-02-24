import os
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bard")

HOME = os.environ.get('HOME', os.path.expanduser('~'))
XDG_CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.join(HOME, '.cache'))
CACHE_DIR = os.path.join(XDG_CACHE_HOME, 'bard')

def clean_cache():
    logger.info(f"Cleaning cache directory: {CACHE_DIR}")
    shutil.rmtree(CACHE_DIR)

def is_running_in_termux():
    return os.environ.get('PREFIX') == '/data/data/com.termux/files/usr'