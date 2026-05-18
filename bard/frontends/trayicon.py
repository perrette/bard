import logging
import threading
from pathlib import Path

from PIL import Image
from pystray import Menu, MenuItem as Item, Icon
from bard.frontends.abstract import AbstractApp
from bard.backends import BACKENDS, available_backends, probe_backend

import bard_data
from desktop_ai_core.frontends.tray import flag_for

_trayicon_logger = logging.getLogger(__name__)


def _format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _progress_bar(position: float, total: float, width: int = 8) -> str:
    if total <= 0:
        return "▱" * width
    filled = max(0, min(width, int(position / total * width)))
    return "▰" * filled + "▱" * (width - filled)


_app_ref = [None]


def _status_header_label(item):
    app = _app_ref[0]
    if app is None:
        return "─"
    player = app.audioplayer
    if player is None:
        return "─"
    elapsed = _format_time(player.current_position_seconds)
    total = _format_time(player.total_duration)
    bar = _progress_bar(player.current_position_seconds, player.total_duration)
    if player.is_playing:
        icon_char = "▶"
    elif player.is_done:
        icon_char = "⏹"
    else:
        icon_char = "⏸"
    return f"{icon_char} {elapsed} / {total}  {bar}"


def _toggle_label(item):
    app = _app_ref[0]
    if app is None or app.audioplayer is None:
        return "▶ Play"
    return "⏸ Pause" if app.audioplayer.is_playing else "▶ Play"


def _callback_toggle(icon, item):
    app = _app_ref[0]
    if app and app.audioplayer and app.audioplayer.is_playing:
        app.callback_pause(icon, item)
    else:
        if app:
            app.callback_play(icon, item)


def _callback_seek_fraction(frac):
    def cb(icon, item):
        app = _app_ref[0]
        if app and app.audioplayer:
            app.audioplayer.jump_to(app.audioplayer.total_duration * frac)
            icon.update_menu()
    return cb


def show_error_dialog(title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception as exc:
        _trayicon_logger.error(f"tkinter unavailable, cannot show dialog: {exc}")
        return

    def _show():
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror(title, message, master=root)
        root.destroy()

    t = threading.Thread(target=_show, daemon=True)
    t.start()


def _format_voice_label(voice) -> str:
    flag = flag_for(voice.language)
    prefix = f"{flag} " if flag else ""
    suffix = f" ({voice.gender[0].upper()})" if voice.gender else ""
    return f"{prefix}{voice.id}{suffix}"


def create_app(backend, player, models=[], jump_back=15, jump_forward=15, backend_kwargs=None, api_keys=None, **options):

    options = {
        "jump_back": jump_back,
        "jump_forward": jump_forward,
        **options,
    }

    app = AbstractApp(backend, player, options, models=models, backend_kwargs=backend_kwargs, api_keys=api_keys, error_callback=show_error_dialog)
    _app_ref[0] = app

    def _make_backend_label(name):
        locality = "local" if BACKENDS[name].is_local else "remote"

        def _label(item):
            ok, reason = probe_backend(name)
            if not ok:
                return f"{name} (unavailable: {reason})"
            return f"{name} ({locality})"

        return _label

    def _make_backend_action(name):
        def _cb(icon, item):
            ok, reason = probe_backend(name)
            if not ok:
                app.logger.warning(f"Backend {name!r} unavailable: {reason}")
                return
            app.switch_backend(name)
            icon.update_menu()

        return _cb

    def _make_backend_checked(name):
        return lambda item: app.backend.name == name

    def _backend_items():
        return tuple(
            Item(
                _make_backend_label(name),
                _make_backend_action(name),
                checked=_make_backend_checked(name),
                radio=True,
            )
            for name in available_backends()
        )

    def _make_model_action(m):
        def _cb(icon, item):
            app.set_model(m)
            icon.update_menu()

        return _cb

    def _make_model_checked(m):
        return lambda item: app.backend.model == m

    def _model_items():
        return tuple(
            Item(m, _make_model_action(m), checked=_make_model_checked(m), radio=True)
            for m in app.backend.list_models()
        )

    def _model_visible(item):
        return bool(app.backend.list_models())

    def _make_voice_action(vid):
        def _cb(icon, item):
            app.set_voice(vid)
            icon.update_menu()

        return _cb

    def _make_voice_checked(vid):
        return lambda item: app.backend.voice == vid

    def _voice_items():
        return tuple(
            Item(
                _format_voice_label(v),
                _make_voice_action(v.id),
                checked=_make_voice_checked(v.id),
                radio=True,
            )
            for v in app.backend.list_voices_meta()
        )

    tts_menu = Item('TTS', Menu(
        Item('Backend', Menu(_backend_items)),
        Item('Model', Menu(_model_items), visible=_model_visible),
        Item('Voice', Menu(_voice_items)),
    ))

    tracks_menu = Item('Tracks', Menu(
        Item('Previous', app.callback_previous_track),
        Item('Next', app.callback_next_track, visible=app.is_processed),
        Item('Delete', app.callback_delete_this_track, visible=app.is_processed),
    ))

    menu = Menu(
        Item('Process Copied Text', app.callback_process_clipboard),
        Item(_status_header_label, lambda *_: None, visible=app.is_processed),
        Item(_toggle_label, _callback_toggle, visible=app.is_processed),
        Item('⏹ Stop', app.callback_stop, visible=app.is_processed),
        Item(f'⏪ {jump_back} s', app.callback_jump_back, visible=app.is_processed),
        Item(f'⏩ {jump_forward} s', app.callback_jump_forward, visible=app.is_processed),
        Item('Seek', Menu(
            Item('Beginning (0%)', _callback_seek_fraction(0)),
            Item('25%', _callback_seek_fraction(0.25)),
            Item('50%', _callback_seek_fraction(0.5)),
            Item('75%', _callback_seek_fraction(0.75)),
        ), visible=app.is_processed),
        Item('Open with external player', app.callback_open_external, visible=app.is_processed),
        tracks_menu,
        tts_menu,
        Item('Options', Menu(
                *(Item(name, app.callback_toggle_option, checked=app.checked)
                    for name in options if isinstance(options[name], bool)),
        )),
        Item('Quit', app.callback_quit),
    )

    if bard_data.__file__ is not None:
        data_folder = Path(bard_data.__file__).parent
    else:
        data_folder = Path(bard_data.__path__[0])

    image = Image.open(data_folder / "share" / "icon.png")

    view = Icon('bard', icon=image, title="Bard", menu=menu)
    view.update_progress = view.update_menu
    app.set_audioplayer(view, player)

    return view
