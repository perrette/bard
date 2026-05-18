import logging
import os
import select
import sys
import termios
import time
import tty

from readchar import key as _key

from bard.frontends.abstract import AbstractApp
from bard.backends import BACKENDS, available_backends, probe_backend
from desktop_ai_core.frontends.terminal import Item, SetValueItem, Menu


_last_key_time: dict[str, float] = {}


def _format_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _progress_bar(position: float, total: float, width: int = 24) -> str:
    if total <= 0:
        return "▱" * width
    frac = max(0.0, min(1.0, position / total))
    filled = int(frac * width)
    return "▰" * filled + "▱" * (width - filled)


def _read_key(fd: int, esc_timeout: float = 0.05) -> str:
    """Read one keypress (including ANSI escape sequences) from `fd`.

    Unlike readchar.readkey(), this does NOT call tcsetattr(TCSAFLUSH)
    on entry — TCSAFLUSH discards anything already buffered in stdin,
    which would eat the byte that select() just signalled as ready and
    force the user to press every key twice. The terminal must already
    be in cbreak mode (caller's responsibility).
    """
    b = os.read(fd, 1)
    if b != b"\x1b":
        return b.decode("utf-8", errors="replace")
    # Possible escape sequence — see if more bytes are coming
    ready, _, _ = select.select([sys.stdin], [], [], esc_timeout)
    if not ready:
        return _key.ESC
    buf = b + os.read(fd, 1)
    if buf[1:2] != b"[":
        return buf.decode("utf-8", errors="replace")
    # CSI sequence; read until a final byte (0x40..0x7E)
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], esc_timeout)
        if not ready:
            break
        c = os.read(fd, 1)
        buf += c
        if 0x40 <= c[0] <= 0x7E:
            break
    return buf.decode("utf-8", errors="replace")


def _playback_mode(view, app):
    _last_key_time.clear()
    fd = sys.stdin.fileno()
    saved_tty = termios.tcgetattr(fd)
    saved_log_disable = logging.root.manager.disable
    jump_hint = app.get_param("jump_back")
    hint_line = f"[space] play/pause  [←→] ±{jump_hint} s  [↑↓] track  [del] del  [q] menu"

    try:
        # Enter alternate screen so the menu and any concurrent log output
        # stay isolated from the dashboard. The original screen is restored
        # verbatim on exit.
        sys.stdout.write("\033[?1049h\033[?25l")
        sys.stdout.flush()
        tty.setcbreak(fd)
        # Suppress logging during the mode so background log/print noise
        # doesn't pile up under the dashboard frame-after-frame.
        logging.disable(logging.CRITICAL)
        # Drain any stray bytes left in stdin (e.g. echo from menu Enter key)
        while True:
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if not r:
                break
            sys.stdin.read(1)

        while True:
            if app.audioplayer is None:
                break
            player = app.audioplayer
            if player.is_done:
                icon = "⏹"
            elif player.is_playing:
                icon = "⏸"
            else:
                icon = "▶"
            pos = player.current_position_seconds
            total = player.total_duration
            line1 = f"{icon}  {_format_time(pos)} / {_format_time(total)}"
            line2 = _progress_bar(pos, total)

            # Always paint from home; clear-line on each row, then clear
            # everything below so any stray output from background threads
            # (audio.py print, etc.) gets wiped on the next frame.
            sys.stdout.write("\033[H")
            sys.stdout.write(f"\033[K{line1}\n")
            sys.stdout.write(f"\033[K{line2}\n")
            sys.stdout.write(f"\033[K{hint_line}")
            sys.stdout.write("\033[J")
            sys.stdout.flush()

            ready, _, _ = select.select([sys.stdin], [], [], 0.25)
            if not ready:
                continue
            ch = _read_key(fd)
            if ch == " ":
                if app.audioplayer is None:
                    break
                if app.audioplayer.is_playing:
                    app.callback_pause(view, None)
                else:
                    app.callback_play(view, None)
            elif ch == _key.LEFT or ch == _key.RIGHT:
                if app.audioplayer is None:
                    break
                now = time.monotonic()
                prev = _last_key_time.get(ch, 0.0)
                if (now - prev) < 0.15:
                    delta = 1.0
                else:
                    delta = float(app.get_param(
                        "jump_back" if ch == _key.LEFT else "jump_forward"))
                _last_key_time[ch] = now
                pos = app.audioplayer.current_position_seconds
                target = pos - delta if ch == _key.LEFT else pos + delta
                app.audioplayer.jump_to(target)
            elif ch == _key.UP:
                app.callback_previous_track(view, None)
            elif ch == _key.DOWN:
                app.callback_next_track(view, None)
            elif ch == _key.DELETE:
                app.callback_delete_this_track(view, None)
                break
            elif ch in ("q", "Q", _key.ESC):
                break
            else:
                continue
    finally:
        logging.disable(saved_log_disable)
        termios.tcsetattr(fd, termios.TCSADRAIN, saved_tty)
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()


class _DynamicItem(Item):
    """Item whose display name is computed from a callable each time it is shown."""

    def __init__(self, name_fn, callback, **kwargs):
        super().__init__("", callback, **kwargs)
        self._name_fn = name_fn

    @property
    def name(self):
        return self._name_fn()

    @name.setter
    def name(self, value):
        pass  # super().__init__ assigns self.name = ""; discard it

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
            name = v.display or v.id
            label = f"{name} [{', '.join(parts)}]" if parts else name
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

    def _open_player(view, item=None):
        if app.audioplayer is not None:
            if app.audioplayer.is_done:
                app.audioplayer.jump_to(0)
            if not app.audioplayer.is_playing:
                app.callback_play(view, None)
        _playback_mode(view, app)

    def _callback_process_then_play(view, item=None):
        app.callback_process_clipboard(view, item)
        if app.audioplayer is not None:
            _playback_mode(view, app)

    def _seek_submenu(view, item):
        def _seek(frac):
            def _cb(v, i=None):
                app.audioplayer.jump_to(app.audioplayer.total_duration * frac)
            return _cb
        items = [
            Item("Beginning (0%)", _seek(0.0)),
            Item("25%", _seek(0.25)),
            Item("50%", _seek(0.5)),
            Item("75%", _seek(0.75)),
            Item("Done", lambda v, i: False),
        ]
        Menu(items, name="Seek")(view, None)

    def _tracks_submenu(view, item):
        items = [
            Item("Previous", app.callback_previous_track),
            Item("Next", app.callback_next_track, visible=app.is_processed),
            Item("Delete", app.callback_delete_this_track, visible=app.is_processed),
            Item("Done", lambda v, i: False),
        ]
        Menu(items, name="Tracks")(view, None)

    menu = Menu([
        Item('Process Copied Text', _callback_process_then_play),
        Item('▶ Play', _open_player, visible=app.is_processed),
        Item('Stop', app.callback_stop, visible=app.is_processed),
        Item(f'⏪ {jump_back} s', app.callback_jump_back, visible=app.is_processed),
        Item(f'⏩ {jump_forward} s', app.callback_jump_forward, visible=app.is_processed),
        Item('Seek', _seek_submenu, visible=app.is_processed),
        Item('Open with external player', app.callback_open_external, visible=app.is_processed),
        Item('Tracks', _tracks_submenu),
        Item('TTS', _tts_submenu),
        Item('Options', submenu_params),
        Item('Quit', app.callback_quit),
        ]
    )

    view = TerminalView(menu, title="Bard")
    app.set_audioplayer(view, player)

    return view