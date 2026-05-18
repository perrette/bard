from pathlib import Path

from PIL import Image
from pystray import Menu, MenuItem as Item, Icon
from bard.frontends.abstract import AbstractApp
from bard.backends import BACKENDS, available_backends, probe_backend

import bard_data


_FLAGS = {
    "en-US": "🇺🇸",
    "en-GB": "🇬🇧",
    "fr-FR": "🇫🇷",
    "de-DE": "🇩🇪",
    "es-ES": "🇪🇸",
    "it-IT": "🇮🇹",
    "ja-JP": "🇯🇵",
    "zh-CN": "🇨🇳",
}


def _flag_for(language: str | None) -> str:
    if language is None:
        return ""
    return _FLAGS.get(language, "")


def _format_voice_label(voice) -> str:
    flag = _flag_for(voice.language)
    prefix = f"{flag} " if flag else ""
    suffix = f" ({voice.gender[0].upper()})" if voice.gender else ""
    return f"{prefix}{voice.id}{suffix}"


def create_app(backend, player, models=[], jump_back=15, jump_forward=15, **options):

    options = {
        "jump_back": jump_back,
        "jump_forward": jump_forward,
        **options,
    }

    app = AbstractApp(backend, player, options, models=models)

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
        tts_menu,
        Item(f'Options', Menu(
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
    app.set_audioplayer(view, player)

    return view
