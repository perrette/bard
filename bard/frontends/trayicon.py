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
    if player.is_done:
        icon_char = "⏹"
    elif player.is_playing:
        icon_char = "⏸"
    else:
        icon_char = "▶"
    return f"{icon_char} {elapsed} / {total}  {bar}"


def _callback_toggle(icon, item):
    app = _app_ref[0]
    if app and app.audioplayer and app.audioplayer.is_playing:
        app.callback_pause(icon, item)
    else:
        if app:
            app.callback_play(icon, item)


def _update_tooltip(view, _player=None):
    app = _app_ref[0]
    if app is None or app.audioplayer is None:
        view.title = "Bard"
        return
    p = app.audioplayer
    if p.is_done:
        ic = "⏹"
    elif p.is_playing:
        ic = "⏸"
    else:
        ic = "▶"
    view.title = f"Bard  {ic} {_format_time(p.current_position_seconds)} / {_format_time(p.total_duration)}"


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
    suffix = f" ({voice.gender[0].upper()})" if voice.gender else ""
    return f"{voice.display or voice.id}{suffix}"


_VENDOR_PREFIX = {
    "openai": "OpenAI",
    "kokoro": "Kokoro",
    "elevenlabs": "ElevenLabs",
    "piper": "Piper",
}

# Menu listing per backend — avoids instantiating non-active backends (which
# may need network / API keys). The active backend's live ``list_models()``
# is preferred when it returns more entries (e.g. ElevenLabs API additions).
_STATIC_MODELS = {
    "openai": ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"],
    "elevenlabs": ["eleven_turbo_v2_5", "eleven_flash_v2_5",
                   "eleven_multilingual_v2", "eleven_v3"],
    "kokoro": [],
    "piper": [],
}


def _vendor_label(name: str) -> str:
    return _VENDOR_PREFIX.get(name, name.capitalize())


def create_app(backend, player, models=[], jump_back=15, jump_forward=15, backend_kwargs=None, api_keys=None, **options):

    options = {
        "jump_back": jump_back,
        "jump_forward": jump_forward,
        **options,
    }

    app = AbstractApp(backend, player, options, models=models, backend_kwargs=backend_kwargs, api_keys=api_keys, error_callback=show_error_dialog)
    _app_ref[0] = app

    def _models_for(name):
        """Models available for backend `name`. Prefers the live list from the
        active backend; otherwise falls back to the static menu listing."""
        if app.backend.name == name:
            try:
                live = list(app.backend.list_models())
            except Exception:
                live = []
            if live:
                return live
        return list(_STATIC_MODELS.get(name, []))

    def _make_set_backend_model(name, model=None):
        def _cb(icon, item):
            ok, reason = probe_backend(name)
            if not ok:
                app.logger.warning(f"Backend {name!r} unavailable: {reason}")
                return
            if app.backend.name != name:
                if not app.switch_backend(name):
                    return
            if model is not None:
                app.set_model(model)
            icon.update_menu()

        return _cb

    def _make_active_check(name, model=None):
        if model is None:
            return lambda item: app.backend.name == name
        return lambda item: (app.backend.name == name
                             and getattr(app.backend, "model", None) == model)

    def _vendor_model_items(name):
        def _items():
            return tuple(
                Item(m,
                     _make_set_backend_model(name, m),
                     checked=_make_active_check(name, m),
                     radio=True)
                for m in _models_for(name)
            )
        return _items

    def _model_items():
        items = []
        for name in available_backends():
            vendor = _vendor_label(name)
            locality = "local" if BACKENDS[name].is_local else "remote"
            base_label = f"{vendor} ({locality})"
            ok, reason = probe_backend(name)
            if not ok:
                items.append(Item(f"{base_label} — unavailable: {reason}",
                                  lambda icon, item: None,
                                  enabled=False))
                continue
            if _models_for(name):
                items.append(Item(base_label, Menu(_vendor_model_items(name))))
            else:
                items.append(Item(base_label,
                                  _make_set_backend_model(name),
                                  checked=_make_active_check(name),
                                  radio=True))
        return tuple(items)

    def _make_voice_action(vid):
        def _cb(icon, item):
            app.set_voice(vid)
            icon.update_menu()

        return _cb

    def _make_voice_checked(vid):
        return lambda item: app.backend.voice == vid

    def _voice_leaf(v):
        return Item(
            _format_voice_label(v),
            _make_voice_action(v.id),
            checked=_make_voice_checked(v.id),
            radio=True,
        )

    def _voice_items():
        from bard.voices import group_by_language
        voices = app.backend.list_voices_meta()
        groups = group_by_language(voices)
        # Flat menu when only one language is present.
        if len(groups) <= 1:
            return tuple(_voice_leaf(v) for v in voices)
        out = []
        for lang, lang_voices in groups.items():
            flag = flag_for(lang)
            label = f"{flag + ' ' if flag else ''}{lang or 'Other'} ({len(lang_voices)})"
            inner = tuple(_voice_leaf(v) for v in lang_voices)
            out.append(Item(label, Menu(*inner)))
        return tuple(out)

    def _tts_label(item):
        vendor = _vendor_label(app.backend.name)
        model = getattr(app.backend, "model", None)
        return f"{vendor} {model}" if model else vendor

    tts_menu = Item(_tts_label, Menu(
        Item('Model', Menu(_model_items)),
        Item('Voice', Menu(_voice_items)),
    ))

    tracks_menu = Item('Tracks', Menu(
        Item('Previous', app.callback_previous_track),
        Item('Next', app.callback_next_track, visible=app.is_processed),
        Item('Delete', app.callback_delete_this_track, visible=app.is_processed),
    ))

    menu = Menu(
        Item('Process Copied Text', app.callback_process_clipboard),
        Item(_status_header_label, _callback_toggle, visible=app.is_processed),
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
    view.update_progress = lambda p=None: _update_tooltip(view, p)
    view.update_state = lambda p=None: view.update_menu()
    app.set_audioplayer(view, player)

    return view
