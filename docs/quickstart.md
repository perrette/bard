# Quickstart

In a terminal:

```bash
bard
```

which defaults to:

```bash
bard --backend openai --voice alloy --model gpt-4o-mini-tts
```

(this assumes the environment variable `OPENAI_API_KEY` is defined)

An icon should show up almost immediately in the system tray, with options to
copy the content of the clipboard (the last thing you copy-pasted) and send that
to the AI model for reading aloud.

<img src="https://raw.githubusercontent.com/perrette/bard/main/docs/app-tray-menu.png" width="300px">

From here you can:

- Feed bard different input sources — see [Input sources](input-sources.md).
- Switch backend, model, or voice from the [tray menu](tray-menu.md).
- Bind a [global keyboard shortcut](keyboard-shortcut.md) to read the clipboard
  from anywhere.

## Terminal mode

There is a terminal version via the `--no-tray` parameter that renders a
keyboard-driven playback dashboard
(`[space]` play/pause, `[←→]` ±jump, `[↑↓]` track, `[del]` delete, `[q]` menu).

For a one-off execution of the program without any controls, use
`--no-interactive` (the older `--no-prompt` is kept as a deprecated alias).
