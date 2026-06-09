# Global keyboard shortcut

In tray mode bard writes its PID to `$XDG_RUNTIME_DIR/bard.pid` (or
`/tmp/bard.pid`) and listens for two signals:

- `SIGUSR1` — read the clipboard (same as the `Process Copied Text` menu entry).
- `SIGUSR2` — toggle play/pause on the current track.

Bind these to keyboard shortcuts in your desktop environment to drive bard from
anywhere. For example, on GNOME (Settings → Keyboard → Custom Shortcuts), bind
`Super+B` to:

```bash
bash -c 'kill -SIGUSR1 $(cat "${XDG_RUNTIME_DIR:-/tmp}/bard.pid")'
```

The `bash -c` wrapper is needed because GNOME's custom shortcuts don't go
through a shell, so command substitution (`$(...)`) and `${...:-default}`
wouldn't otherwise be expanded.

This delegates the hotkey to the DE rather than grabbing keys inside the
process, so it works on Wayland too.
