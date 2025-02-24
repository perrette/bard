import shutil
from bard.frontends.abstract import AbstractApp

class Item:
    def __init__(self, name, callback, checked=None, checkable=False, visible=True, help=""):
        self.name = name
        self.callback = callback
        self.checkable = checkable or (checked is not None)
        self.checked = (checked if callable(checked) else lambda item: checked)
        self.help = help
        self.visible = visible if callable(visible) else lambda item: visible

    def __str__(self):
        return self.name

class Menu:
    def __init__(self, items, name=None, help=""):
        self.items = items
        self.name = name
        self.help = help
        self.choices = {}

    def __call__(self, app, _):
        while self.prompt(app):
            pass

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
            item.callback(app, item)
            return True

        elif choice in ("quit", "q"):
            return False
        else:
            return True

class TerminalView:
    def __init__(self, menu, title=""):
        self.menu = menu
        self.title = title
        self.is_running = False

    def run(self):
        self.is_running = True
        while self.is_running:
            self.menu.show(self)
            self.is_running = self.menu.prompt(self)

    def stop(self):
        self.is_running = False

    def update_menu(self):
        self.menu.show(self)

# Function to clear the terminal line
def clear_line():
    # Get terminal width
    terminal_width = shutil.get_terminal_size().columns
    print("\r" + " " * terminal_width, end="")  # Clear the line
    print("\r", end="")  # Return cursor to the beginning of the line

def show_progress(player):
    clear_line()
    print(f"Playing: {player.current_position / player.fs:.2f} s / {len(player.data) / player.fs:.2f} s", end="\r")


def create_app(model, player, models=[], jump_back=15, jump_forward=15,
               clean_cache_on_exit=False, external_player=None):

    options = {
        "clean_cache_on_exit": clean_cache_on_exit,
        "jump_back": jump_back,
        "jump_forward": jump_forward,
        "external_player": external_player,
    }

    app = AbstractApp(model, player, options, models=models)

    menu = Menu([
        Item('Process Copied Text', app.callback_process_clipboard),
        Item('Play', app.callback_play, visible=app.show_play),
        Item('Pause', app.callback_pause, visible=app.show_pause),
        Item('Stop', app.callback_stop, visible=app.is_processed),
        Item(f'Jump Back {jump_back} s', app.callback_jump_back, visible=app.is_processed),
        Item(f'Jump Forward {jump_forward} s', app.callback_jump_forward, visible=app.is_processed),
        Item(f'Open with external player', app.callback_open_external, visible=external_player is not None),
        Item(f'Options', Menu(
                [Item(name, app.callback_toggle_option, checked=app.checked)
                    for name in options if isinstance(options[name], bool)])
        ),
        Item('Quit', app.callback_quit),
        ]
    )

    view = TerminalView(menu, title="Bard")
    view.show_progress = show_progress
    app.set_audioplayer(view, player)

    return view