from pathlib import Path

from PIL import Image
import pyperclip
import pystray

from bard.util import logger, clean_cache
from bard.input import preprocess_input_text
from bard.audio import AudioPlayer
import bard_data

def create_app(model, models=[], default_audio_files=None, jump_back=15, jump_forward=15,
               clean_cache_on_exit=False, text=None, audio_files=None, external_player=None):

    def callback_process_clipboard(icon, item):
        logger.info('Processing clipboard...')
        text = pyperclip.paste()
        logger.info(f'{len(text)} characters copied')
        text = preprocess_input_text(text)

        # clean-up the audio
        if icon._audioplayer is not None:
            icon._audioplayer.stop()
            icon._audioplayer = None
        try:
            icon._audioplayer = AudioPlayer.from_files(icon._model.text_to_audio_files(text))
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
        icon.stop()
        icon._audioplayer.stop()
        if icon._options["clean_cache_on_exit"]:
            clean_cache()

    def callback_toggle_option(icon, item):
        icon._options[str(item)] = not icon._options[str(item)]

    def callback_open_external(icon, item):
        logger.info('Opening with external player...')
        if icon._audioplayer is None:
            logger.error('No audio to play')
            return
        icon._audioplayer.open_external(external_player)

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
        pystray.MenuItem(f'Open with external player', callback_open_external, visible=external_player is not None),
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

    return icon
