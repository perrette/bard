import shutil
import datetime

from bard.util import logger
from bard.frontends.abstract import AbstractApp

class Item:
    def __init__(self, name, callback, checked=None, checkable=False, visible=True, help=""):
        self.name = name
        self._callback = callback
        self.checkable = checkable or (checked is not None)
        self.checked = (checked if callable(checked) else lambda item: checked)
        self.help = help
        self.visible = visible if callable(visible) else lambda item: visible

    def __call__(self, app, item):
        return self._callback(app, item)

    def __str__(self):
        return self.name

class Menu:
    def __init__(self, items, name=None, help=""):
        self.items = items
        self.name = name
        self.help = help
        self.choices = {}
        self.is_active_menu = False

    def __call__(self, app, _):
        self.is_active_menu = True
        while app.is_running and self.is_active_menu:
            self.show(app)
            self.prompt(app)

    def show(self, app):
        print(f"\n{self.name or 'Options:'}")

        count = 0
        for item in self.items:
            if not item.visible(item):
                continue
            count += 1
            ticked = " "
            if item.checkable and item.checked(item):
                ticked = "✓"
            print(f"{ticked} {count}. {item.help or item.name}")
            self.choices[str(count)] = item
            self.choices[item.name] = item

    def prompt(self, app, title=None):

        if getattr(app, "_player", None):
            app.update_progress(app._player)

        choice = input("\nChoose an option: ")

        if choice in self.choices:
            item = self.choices[choice]
            print(item)
            ans = item(app, item)
            if isinstance(ans, bool):
                self.is_active_menu = ans

        elif choice in ("quit", "q"):
            self.is_active_menu = False

        else:
            return print(f"Invalid choice: {choice}")

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


def create_app(model, player, models=[], jump_back=15, jump_forward=15,
               clean_cache_on_exit=False, external_player=None):

    options = {
        "clean_cache_on_exit": clean_cache_on_exit,
        "jump_back": jump_back,
        "jump_forward": jump_forward,
        "external_player": external_player,
    }

    app = AbstractApp(model, player, options, models=models)

    submenu_params = Menu([
            *(Item(name, app.callback_toggle_option, checked=app.checked)
                    for name in options if isinstance(options[name], bool)),
            Item("Done", lambda x,y=None: False) ])

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
        Item(f'Options', submenu_params),
        Item('Quit', app.callback_quit),
        ]
    )

    view = TerminalView(menu, title="Bard")
    app.set_audioplayer(view, player)

    return view