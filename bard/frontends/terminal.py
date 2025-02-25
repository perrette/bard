import shutil
from bard.frontends.abstract import AbstractApp

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn


class ProgressBar:
    def __init__(self, total_duration, description="Playing"):
        self.console = Console()
        self.total_duration = total_duration
        self.current_position = 0
        self.description = description
        self.progress = Progress(
            TextColumn(f"[progress.description]{{task.description}}"),
            TimeElapsedColumn(),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
        )
        self.task = self.progress.add_task(self.description, total=self.total_duration)

    def update(self, new_position, total_duration=None):
        self.current_position = new_position
        with self.progress:
            self.progress.update(self.task, completed=self.current_position)

            if total_duration is not None and total_duration != self.total_duration:
                self.total_duration = total_duration
                self.progress.update(self.task, total=total_duration)

        self.progress.refresh()

    # def __del__(self):
    #     if self.progress is not None:
    #         self.progress.refresh()
    #     # self.progress.stop()


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
    def __init__(self, menu, title="", progressbar=None):
        self.menu = menu
        self.title = title
        self.is_running = False
        self.progressbar = progressbar

    def run(self):
        self.is_running = True
        self.menu.is_active_menu = True
        while self.is_running:
            self.menu(self, None)
            self.is_running &= (self.menu.is_active_menu is not False)

    def stop(self):
        self.is_running = False

    def update_menu(self):
        self.menu.show(self)

    def update_progress(self, player):
        if not self.is_running:
            self.progressbar = None
            return
        if self.progressbar is None:
            self.progressbar = ProgressBar(player.total_duration)
        self.progressbar.update(player.current_position_seconds, player.total_duration)

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
        Item(f'Open with external player', app.callback_open_external, visible=lambda x: app.is_processed(x) and external_player is not None),
        Item('Resume Last Audio', app.callback_previous_track, visible=lambda x: not app.is_processed()),
        Item(f'Options', submenu_params),
        Item('Quit', app.callback_quit),
        ]
    )

    view = TerminalView(menu, title="Bard")
    app.set_audioplayer(view, player)

    return view