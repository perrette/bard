import sys, sysconfig
import argparse
import bard_data
import os
from desktop_ai_core.install import install_desktop_file

def main():

    parser = argparse.ArgumentParser("Install the desktop file for the bard package. Any arguments to this script will be passed on to `bard`.")
    parser.add_argument("--name", help="The title of the desktop app", default="Bard")
    parser.add_argument("--startup-wm-class")
    parser.add_argument("--no-terminal", action="store_false", dest="terminal", help="Don't show the terminal")
    o, rest = parser.parse_known_args()
    o.arguments = rest

    SOURCE_BARD_DATA = os.path.dirname(bard_data.__file__) if bard_data.__file__ else bard_data.__path__[0]

    with open(os.path.join(SOURCE_BARD_DATA, 'templates', 'bard.desktop')) as f:
        template = f.read()

    bin_folder = sysconfig.get_path("scripts")
    icon_folder = os.path.join(SOURCE_BARD_DATA, 'share')
    options = ' ' + ' '.join(o.arguments) if o.arguments else ''

    try:
        desktop_filepath = install_desktop_file(
            template=template,
            name=o.name,
            icon_folder=icon_folder,
            bin_folder=bin_folder,
            terminal=o.terminal,
            startup_wm_class=o.startup_wm_class,
            options=options,
        )
    except NotImplementedError as e:
        print(str(e), file=sys.stderr)
        sys.exit(0)

    print("Writing GNOME desktop file:", desktop_filepath)

if __name__ == "__main__":
    main()
