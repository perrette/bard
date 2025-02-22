import os
from pathlib import Path
import logging

import pystray
from PIL import Image
# from pydub import AudioSegment
# from pydub.playback import play
import pyperclip

import bard_data
from bard.models import OpenaiAPI
from bard.audio import AudioPlayer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bard")

def get_model(voice=None, model=None, output_format="mp3", openai_api_key=None, backend="openaiapi"):
    if backend == "openaiapi":
        return OpenaiAPI(voice=voice, model=model, output_format=output_format, api_key=openai_api_key)
    else:
        raise ValueError(f"Unsupported backend: {backend}")

def create_app(model, models=[], default_file=None):

    # icon = pystray.Icon('bard', title='Bard')
    # icon.icon = Image.open(Path(bard_data.__file__).parent / "share" / "icon.png")

    # # initialize the app state
    # icon._model = model
    # icon._audioplayer = None
    # icon._jump_back = 15
    # icon._jump_forward = 15

    def callback_process_clipboard(icon, item):
        logger.info('Processing clipboard...')
        text = pyperclip.paste()
        icon._audioplayer = AudioPlayer.from_files(icon._model.text_to_audio_files(text))
        logger.info('Done!')
        icon.update_menu()

    def callback_play(icon, item):
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
        icon.stop()

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

    menu = pystray.Menu(
        pystray.MenuItem('Process Copied Text', callback_process_clipboard),
        pystray.MenuItem('Play', callback_play, visible=show_play),
        pystray.MenuItem('Pause', callback_pause, visible=show_pause),
        pystray.MenuItem('Stop', callback_stop, visible=is_processed),
        pystray.MenuItem('Jump Back', callback_jump_back, visible=is_processed),
        pystray.MenuItem('Jump Forward', callback_jump_forward, visible=is_processed),
        pystray.MenuItem('Quit', callback_quit),
    )

    image = Image.open(Path(bard_data.__file__).parent / "share" / "icon.png")
    icon = pystray.Icon('bard', icon=image, title="Bard", menu=menu)

    icon._model = model
    if default_file is not None:
        icon._audioplayer = AudioPlayer.from_files([default_file])
    else:
        icon._audioplayer = None
    icon._jump_back = 1
    icon._jump_forward = 1

    return icon


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default=None, help="Voice to use")
    parser.add_argument("--model", default=None, help="Model to use")
    parser.add_argument("--output-format", default="mp3", help="Output format")
    parser.add_argument("--openai-api-key", default=None, help="OpenAI API key")
    parser.add_argument("--backend", default="openaiapi", help="Backend to use")
    parser.add_argument("--default-file", default=None, help="Default file to play")

    o = parser.parse_args()

    model = get_model(voice=o.voice, model=o.model, output_format=o.output_format, openai_api_key=o.openai_api_key, backend=o.backend)

    app = create_app(model, default_file=o.default_file)
    app.run()

if __name__ == "__main__":
    main()