from pathlib import Path

from PIL import Image
from pystray import Menu, MenuItem as Item, Icon
from bard.frontends.abstract import AbstractApp

import bard_data

def create_app(model, player, models=[], jump_back=15, jump_forward=15, **options):

    options = {
        "jump_back": jump_back,
        "jump_forward": jump_forward,
        **options,
    }

    app = AbstractApp(model, player, options, models=models)

    menu = Menu(
        Item('Process Copied Text', app.callback_process_clipboard),
        Item('Play', app.callback_play, visible=app.show_play),
        Item('Pause', app.callback_pause, visible=app.show_pause),
        Item('Stop', app.callback_stop, visible=app.is_processed),
        Item(f'Jump Back {jump_back} s', app.callback_jump_back, visible=app.is_processed),
        Item(f'Jump Forward {jump_forward} s', app.callback_jump_forward, visible=app.is_processed),
        Item(f'Open with external player', app.callback_open_external, visible=app.is_processed),
        Item('Previous audio', app.callback_previous_track),
        Item('Next audio', app.callback_next_track, visible=app.is_processed),
        Item('Delete audio', app.callback_delete_this_track, visible=app.is_processed),
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
    app.set_audioplayer(view, player)

    return view
