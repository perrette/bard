import shutil
import datetime

from bard.util import logger
from bard.frontends.abstract import AbstractApp
from bard.backends import BACKENDS, available_backends, probe_backend
from desktop_ai_core.frontends.terminal import Item, SetValueItem, Menu

class TerminalView:
    backend = "terminal"

    def __init__(self, menu, title=""):
        self.menu = menu
        self.title = title
        self.is_running = False

    def run(self):
        self.is_running = True
        self.menu.is_active_menu = True
        try:
            while self.is_running:
                self.menu(self, None)
                self.is_running &= (self.menu.is_active_menu is not False)
        except KeyboardInterrupt:
            if getattr(self, "_player", None) and self._player.is_playing:
                self._player.stop()
            else:
                self.is_running = False

    def stop(self):
        self.is_running = False

    def update_menu(self):
        pass
        # self.menu.show(self)
        # if getattr(self, "_player", None):
        #     self.update_progress(self._player)

    def update_progress(self, player):
        try:
            if not self.is_running:
                print("")
                return
            # if self.progressbar is None:
            clear_line()
            print(f"\rPlaying {format_time(player.current_position_seconds)} / {format_time(player.total_duration)}", end="")
        except Exception as e:
            logger.error(e)
            raise


def format_time(seconds):
    dt = datetime.timedelta(seconds=int(seconds))
    return str(dt)


# Function to clear the terminal line
def clear_line():
    # Get terminal width
    terminal_width = shutil.get_terminal_size().columns
    print("\r" + " " * terminal_width, end="")  # Clear the line
    print("\r", end="")  # Return cursor to the beginning of the line

def show_progress(player):
    clear_line()
    print(f"Playing: {player.current_position_seconds:.2f} s / {player.total_duration:.2f} s", end="\r")


def create_app(backend, player, models=[],
               jump_back=15, jump_forward=15, backend_kwargs=None, api_keys=None, **options):

    options = {
        "jump_back": jump_back,
        "jump_forward": jump_forward,
        **options }

    app = AbstractApp(backend, player, options, models=models, backend_kwargs=backend_kwargs, api_keys=api_keys)

    def _backend_submenu(view, item):
        items = []
        for name in available_backends():
            backend_cls = BACKENDS[name]
            locality = "local" if backend_cls.is_local else "remote"
            ok, reason = probe_backend(name)
            if ok:
                label = f"{name} ({locality})"
                def _cb(view, item, _name=name):
                    app.switch_backend(_name)
                items.append(Item(label, _cb,
                                  checkable=True,
                                  checked=lambda item, _name=name: app.backend.name == _name,
                                  help=label))
            else:
                label = f"{name} (unavailable: {reason})"
                def _unavail_cb(view, item, _name=name, _reason=reason):
                    print(f"Backend {_name!r} unavailable: {_reason}")
                items.append(Item(label, _unavail_cb, help=label))
        items.append(Item("Done", lambda v, i: False))
        Menu(items, name="Backend")(view, None)

    def _model_submenu(view, item):
        models_list = app.backend.list_models()
        if not models_list:
            print("No models available for current backend.")
            return
        items = []
        for m in models_list:
            def _cb(view, item, _m=m):
                app.set_model(_m)
            items.append(Item(m, _cb,
                              checkable=True,
                              checked=lambda item, _m=m: app.backend.model == _m,
                              help=m))
        items.append(Item("Done", lambda v, i: False))
        Menu(items, name="Model")(view, None)

    def _voice_submenu(view, item):
        voices = app.backend.list_voices_meta()
        items = []
        for v in voices:
            parts = [x for x in (v.language, v.gender) if x is not None]
            label = f"{v.id} [{', '.join(parts)}]" if parts else v.id
            def _cb(view, item, _vid=v.id):
                app.set_voice(_vid)
            items.append(Item(label, _cb,
                              checkable=True,
                              checked=lambda item, _vid=v.id: app.backend.voice == _vid,
                              help=label))
        items.append(Item("Done", lambda v, i: False))
        Menu(items, name="Voice")(view, None)

    _tts_menu_items = [
        Item("Backend", _backend_submenu, help="TTS Backend"),
        Item("Model", _model_submenu, help="TTS Model",
             visible=lambda item: bool(app.backend.list_models())),
        Item("Voice", _voice_submenu, help="TTS Voice"),
        Item("Done", lambda v, i: False),
    ]

    def _tts_submenu(view, item):
        Menu(_tts_menu_items, name="TTS")(view, None)

    submenu_params = Menu([
            *(Item(name, app.callback_toggle_option, checked=app.checked) if isinstance(options[name], bool)
              else
              SetValueItem(name, lambda view, item: app.set_param(item.name, item.value(item)),
                           value=app.get_param,
                           type=type(options[name]) if options[name] is not None else None)
              for name in options),
            Item("Done", lambda x, y=None: False) ])

    menu = Menu([
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
        Item('TTS', _tts_submenu),
        Item(f'Options', submenu_params),
        Item('Quit', app.callback_quit),
        ]
    )

    view = TerminalView(menu, title="Bard")
    app.set_audioplayer(view, player)

    return view