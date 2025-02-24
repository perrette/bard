from pathlib import Path

from PIL import Image
from pystray import Menu, MenuItem as Item, Icon
from bard.frontends.abstract import AbstractApp
from bard.frontends.terminal import show_progress

import bard_data

def create_app(model, player, models=[], jump_back=15, jump_forward=15,
               clean_cache_on_exit=False, external_player=None):

    options = {
        "clean_cache_on_exit": clean_cache_on_exit,
        "jump_back": jump_back,
        "jump_forward": jump_forward,
        "external_player": external_player,
    }

    app = AbstractApp(model, player, options, models=models)

    menu = Menu(
        Item('Process Copied Text', app.callback_process_clipboard),
        Item('Play', app.callback_play, visible=app.show_play),
        Item('Pause', app.callback_pause, visible=app.show_pause),
        Item('Stop', app.callback_stop, visible=app.is_processed),
        Item(f'Jump Back {jump_back} s', app.callback_jump_back, visible=app.is_processed),
        Item(f'Jump Forward {jump_forward} s', app.callback_jump_forward, visible=app.is_processed),
        Item(f'Open with external player', app.callback_open_external, visible=external_player is not None),
        Item(f'Options', Menu(
                *(Item(name, app.callback_toggle_option, checked=app.checked)
                    for name in options if isinstance(options[name], bool)))
        ),
        Item('Quit', app.callback_quit),
    )

    if bard_data.__file__ is not None:
        data_folder = Path(bard_data.__file__).parent
    else:
        data_folder = Path(bard_data.__path__[0])

    image = Image.open(data_folder / "share" / "icon.png")

    view = Icon('bard', icon=image, title="Bard", menu=menu)
    view.show_progress = show_progress
    app.set_audioplayer(view, player)

    return view
