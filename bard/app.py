import os
import sys
from pathlib import Path
import re
from PIL import Image
import pyperclip

import bard_data
from bard.models import OpenaiAPI
from bard.audio import AudioPlayer
from bard.util import logger, clean_cache as _clean_cache, CACHE_DIR
from bard.input import read_text_from_pdf

def get_model(voice=None, model=None, output_format="mp3", openai_api_key=None, backend="openaiapi", chunk_size=None):
    if backend == "openaiapi":
        return OpenaiAPI(voice=voice, model=model, output_format=output_format, api_key=openai_api_key, max_length=chunk_size)
    else:
        raise ValueError(f"Unsupported backend: {backend}")

def create_app(model, models=[], default_audio_files=None, jump_back=15, jump_forward=15, resume=False, clean_cache_on_exit=False, text=None, audio_files=None):

    import pystray

    def callback_process_clipboard(icon, item):
        logger.info('Processing clipboard...')
        text = pyperclip.paste()
        logger.info(f'{len(text)} characters copied')
        # clean-up the audio
        if icon._audioplayer is not None:
            icon._audioplayer.stop()
            icon._audioplayer = None
        try:
            icon._audioplayer = AudioPlayer.from_files(icon._model.text_to_audio_files(text),
                                                       callback_loop=lambda player: player.play())
            icon._audioplayer.on_done(lambda x: icon.update_menu()).play()
            logger.info('Done!')
        finally:
            icon.update_menu()

    def callback_play(icon, item):
        if icon._audioplayer is None:
            logger.error('No audio to play')
            return
        logger.info('Playing...')
        icon._audioplayer.on_done(lambda x: icon.update_menu()).play()
        logger.info('Exiting callback...')

    def callback_pause(icon, item):
        logger.info('Pausing...')
        icon._audioplayer.pause()

    def callback_stop(icon, item):
        logger.info('Stopping...')
        icon._audioplayer.stop()

    def callback_jump_back(icon, item):
        logger.info('Jumping back...')
        position = icon._audioplayer.current_position / icon._audioplayer.fs
        print("current_position", icon._audioplayer.current_position, "fs", "or", position, "seconds")
        print("jumping to", position - icon._jump_back, "(seconds)")

        icon._audioplayer.jump_to(position - icon._jump_back)

    def callback_jump_forward(icon, item):
        logger.info('Jumping forward...')
        position = icon._audioplayer.current_position / icon._audioplayer.fs
        print("current_position", icon._audioplayer.current_position, "fs", "or", position, "seconds")
        print("jumping to", position + icon._jump_forward, "(seconds)")
        icon._audioplayer.jump_to(position + icon._jump_forward)

    def callback_quit(icon, item):
        logger.info('Quitting...')
        if icon._options["clean_cache_on_exit"]:
            _clean_cache()
        icon.stop()

    def callback_toggle_option(icon, item):
        icon._options[str(item)] = not icon._options[str(item)]

    def is_processed(item):
        return icon._audioplayer is not None

    def show_pause(item):
        if not is_processed(item):
            return False
        return icon._audioplayer.is_playing

    def show_play(item):
        if not is_processed(item):
            return False
        return not icon._audioplayer.is_playing and not icon._audioplayer.is_done

    options = {
        "clean_cache_on_exit": clean_cache_on_exit,
    }

    menu = pystray.Menu(
        pystray.MenuItem('Process Copied Text', callback_process_clipboard),
        pystray.MenuItem('Play', callback_play, visible=show_play),
        pystray.MenuItem('Pause', callback_pause, visible=show_pause),
        pystray.MenuItem('Stop', callback_stop, visible=is_processed),
        pystray.MenuItem(f'Jump Back {jump_back} s', callback_jump_back, visible=is_processed),
        pystray.MenuItem(f'Jump Forward {jump_forward} s', callback_jump_forward, visible=is_processed),
        pystray.MenuItem(f'Options', pystray.Menu(
                *(pystray.MenuItem(name, callback_toggle_option, checked=lambda item: icon._options[str(item)])
                    for name in options if isinstance(options[name], bool)))
        ),
        pystray.MenuItem('Quit', callback_quit),
    )

    if bard_data.__file__ is not None:
        data_folder = Path(bard_data.__file__).parent
    else:
        data_folder = Path(bard_data.__path__[0])

    image = Image.open(data_folder / "share" / "icon.png")
    icon = pystray.Icon('bard', icon=image, title="Bard", menu=menu)

    icon._model = model
    icon._options = options

    icon._audioplayer = None

    icon._jump_back = jump_back
    icon._jump_forward = jump_forward

    # leave the rest to the app otherwise this is blocking
    if text:
        pyperclip.copy(text)
        callback_process_clipboard(icon, None)

    elif audio_files:
        icon._audioplayer = AudioPlayer.from_files(audio_files)
        callback_play(icon, None)

    elif default_audio_files:
        icon._audioplayer = AudioPlayer.from_files(default_audio_files)

    # scan the cache directory for the most recent files
    # use the pattern f"chunk_{timestamp}_{i}.{self.output_format}"
    # e.g. chunk_2025-02-22T010457.819224_1.mp3
    # and keep only the latest timestamp
    # sort them by index {i} which may occupy more than one digit
    elif resume:
        all_files = list(Path(CACHE_DIR).glob("chunk_*.mp3"))
        all_files.sort()
        try:
            last_file = all_files[-1]
            timestamp = re.search(r'chunk_(\d{4}-\d{2}-\d{2}T\d{6}\.\d{6})_(\d+)\..', str(last_file)).groups()[0]
            default_audio_files = [f for f in all_files if f.name.startswith(f"chunk_{timestamp}")]
        except IndexError:
            logger.error("No files found in the cache directory")
            default_audio_files = []
        except AttributeError:
            logger.error(f"Failed to parse the timestamp from the file name: {last_file}")
            # only keep the last file
            default_audio_files = [last_file]

        if default_audio_files:
            icon._audioplayer = AudioPlayer.from_files(default_audio_files)

    return icon


def main():
    import argparse
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group("API Backend")
    group.add_argument("--voice", default=None, help="Voice to use")
    group.add_argument("--model", default=None, help="Model to use")
    group.add_argument("--output-format", default="mp3", help="Output format")
    group.add_argument("--openai-api-key", default=None, help="OpenAI API key")
    group.add_argument("--backend", default="openaiapi", help="Backend to use")
    group.add_argument("--chunk-size", default=500, type=int, help="Max number of characters sent in one request")

    group = parser.add_argument_group("Frontend")
    group.add_argument("--no-tray", action="store_true", help="Don't show the tray icon. Terminal only. At the moment this launched a one-time audio player.")

    group = parser.add_argument_group("Player")
    group.add_argument("--jump-back", type=int, default=15, help="Jump back time in seconds")
    group.add_argument("--jump-forward", type=int, default=15, help="Jump forward time in seconds")

    group = parser.add_argument_group("Player's files")
    parser.add_argument("--default-audio-file", nargs="+", help="Default audio file(s) to pre-load in the player")
    parser.add_argument("--resume", action="store_true", help="Resume the last played file (if --default-file is not provided)")
    parser.add_argument("--clean-cache-on-exit", action="store_true", help="Clean the cache directory on exit")

    group = parser.add_argument_group("Kick-start")
    group = group.add_mutually_exclusive_group()
    group.add_argument("--clipboard", help="Past text from clipboard to speak right away", action="store_true")
    group.add_argument("--text", help="Text to speak right away")
    group.add_argument("--text-file", help="Text file to read along.")
    group.add_argument("--html-file", help="HTML file to read along.")
    group.add_argument("--url", help="URL to fetch and read along.")
    group.add_argument("--pdf-file", help="PDF File to read along (pdf2text from poppler is used).")
    group.add_argument("--audio-file", nargs="+", help="audio file(s) to play right away")

    o = parser.parse_args()

    model = get_model(voice=o.voice, model=o.model, output_format=o.output_format, openai_api_key=o.openai_api_key, backend=o.backend, chunk_size=o.chunk_size)

    if o.url:
        from bard.html import extract_text_from_url
        o.text = extract_text_from_url(o.url)

    elif o.html_file:
        from bard.html import extract_text_from_html
        o.text = extract_text_from_html(open(o.html_file).read())

    elif o.text_file:
        with open(o.text_file) as f:
            o.text = f.read()

    elif o.clipboard:
        o.text = pyperclip.paste()

    elif o.pdf_file:
        o.text = read_text_from_pdf(o.pdf_file)


    if o.no_tray:
        if o.audio_file:
            player = AudioPlayer.from_files(o.audio_file)
        elif o.text:
            player = AudioPlayer.from_files(model.text_to_audio_files(o.text), callback_loop=lambda player: player.play())
        else:
            parser.error("No files or text provided to play. Exiting...")
            sys.exit(1)

        player.play()
        player.wait()

        if o.clean_cache_on_exit:
            _clean_cache()

    else:
        app = create_app(model, default_audio_files=o.default_audio_file, jump_back=o.jump_back, jump_forward=o.jump_forward, text=o.text,
                        resume=o.resume, audio_files=o.audio_file, clean_cache_on_exit=o.clean_cache_on_exit)
        app.run()

if __name__ == "__main__":
    main()