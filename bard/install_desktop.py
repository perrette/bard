import os, sys, platform, sysconfig
import argparse
import bard_data

def main():

    # Check if the current platform is Linux
    if platform.system() != "Linux":
        print("This package is only supported on Linux systems.", file=sys.stderr)
        sys.exit(0)

    parser = argparse.ArgumentParser("Install the desktop file for the bard package. Any arguments to this script will be passed on to `bard`.")
    parser.add_argument("--name", help="The title of the desktop app", default="Bard")
    parser.add_argument("--startup-wm-class")
    parser.add_argument("--no-terminal", action="store_false", dest="terminal", help="Don't show the terminal")
    o, rest = parser.parse_known_args()
    o.arguments = rest

    # if not o.terminal and "--app" not in o.arguments:
    #     o.arguments.append("--app")
    # if not o.terminal and "--no-prompt" not in o.arguments:
    #     o.arguments.append("--no-prompt")

    SOURCE_BARD_DATA = os.path.dirname(bard_data.__file__) if bard_data.__file__ else bard_data.__path__[0]

    HOME = os.environ.get('HOME',os.path.expanduser('~'))
    XDG_SHARE = os.environ.get('XDG_DATA_HOME', os.path.join(HOME, '.local','share'))
    XDG_APP_DATA = os.path.join(XDG_SHARE, 'applications')

    # Create the directory if it doesn't exist
    os.makedirs(XDG_APP_DATA, exist_ok=True)

    with open(os.path.join(SOURCE_BARD_DATA, 'templates', 'bard.desktop')) as f:
        template = f.read()

    simple_name = o.name.lower().replace(' ','-').replace(os.path.sep, '-')
    bin_folder = sysconfig.get_path("scripts")
    icon_folder = os.path.join(SOURCE_BARD_DATA, 'share')
    desktop_filecontent = template.format(icon_folder=icon_folder, bin_folder=bin_folder,
                                          name=o.name, terminal=str(o.terminal).lower(),
                                          StartupWMClass=o.startup_wm_class or f"crx_mpnasdandanpmm_{simple_name}",
                                          options=' ' + ' '.join(o.arguments) if o.arguments else '')

    desktop_filepath = os.path.join(XDG_APP_DATA, f'{simple_name}.desktop')
    print("Writing GNOME desktop file:", desktop_filepath)
    with open(desktop_filepath, "w") as f:
        f.write(desktop_filecontent)

if __name__ == "__main__":
    main()