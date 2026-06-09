[![pypi](https://img.shields.io/pypi/v/bard-cli)](https://pypi.org/project/bard-cli)
![](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fperrette%2Fbard%2Frefs%2Fheads%2Fmain%2Fpyproject.toml)
[![tests](https://github.com/perrette/bard/actions/workflows/tests.yml/badge.svg)](https://github.com/perrette/bard/actions/workflows/tests.yml)
[![docs](https://img.shields.io/badge/docs-perrette.github.io%2Fbard-blue)](https://perrette.github.io/bard/)

# Bard  <img src="https://github.com/perrette/bard/raw/main/bard_data/share/icon.png" width=48px>

Bard is a text-to-speech client that integrates on the desktop.

<!-- intro-start -->
- **Multiple input sources.** Feed bard plain text, the clipboard, a URL, an HTML
  file, or a PDF — it extracts the readable content (with
  [readability](https://pypi.org/project/readability-lxml)) and speaks it. Useful
  for reading paywalled articles via "View Page Source".
- **Four TTS backends.** OpenAI and ElevenLabs (remote, API key) plus Kokoro and
  Piper (local, free, offline, multilingual). Switch backend, model, and voice
  at runtime from the tray menu without restarting.
- **Desktop player.** A system-tray icon with playback controls, or a
  keyboard-driven terminal dashboard with `--no-tray`. A global shortcut can
  read the clipboard from anywhere (works on Wayland too).
- **Batch or interactive.** Pass `-o file.mp3` to synthesise straight to an audio
  file and exit, or run interactively and drive playback from the tray.
<!-- intro-end -->

## 📖 Documentation

Full documentation lives at **<https://perrette.github.io/bard/>**:

- [Installation](https://perrette.github.io/bard/installation/) (incl. system dependencies)
- [Quickstart](https://perrette.github.io/bard/quickstart/)
- [Backends & voices](https://perrette.github.io/bard/backends/)
- [Tray menu](https://perrette.github.io/bard/tray-menu/)
- Guides: [input sources](https://perrette.github.io/bard/input-sources/),
  [batch render](https://perrette.github.io/bard/batch-render/),
  [global keyboard shortcut](https://perrette.github.io/bard/keyboard-shortcut/),
  [fine-tuning](https://perrette.github.io/bard/fine-tuning/),
  [player](https://perrette.github.io/bard/player/),
  [Android](https://perrette.github.io/bard/android/)

## Install

Install the system dependencies, then the app with all optional backends:

```bash
sudo apt-get install portaudio19-dev xclip #  portaudio19-dev becomes portaudio with Homebrew
sudo apt install libcairo-dev libgirepository1.0-dev gir1.2-appindicator3-0.1  # Ubuntu ONLY (not needed on MacOS)
pip install PyGObject # Ubuntu ONLY (not needed on MacOS)

pip install bard-cli[all]          # OpenAI, ElevenLabs, Kokoro (no Piper)
pip install bard-cli[all-local]    # all of the above + Piper
```

See the [installation page](https://perrette.github.io/bard/installation/) for
individual backend extras and the GNOME launcher.

## Quickstart

```bash
bard
```

defaults to `bard --backend openai --voice alloy --model gpt-4o-mini-tts`
(assuming `OPENAI_API_KEY` is set). An icon shows up in the system tray with an
option to read the clipboard aloud.

<img src=https://raw.githubusercontent.com/perrette/bard/main/docs/app-tray-menu.png width=300px>

You can also do a one-off reading:

```bash
bard --text "Hello world, how are you today"
bard --clipboard
bard --url "example.com"
bard --pdf-file /path/to/document.pdf
```

See the [quickstart](https://perrette.github.io/bard/quickstart/) and
[input sources](https://perrette.github.io/bard/input-sources/) pages for more.

## From the same author

A few related tools I maintain, useful in a Markdown-based scientific workflow.

**Scientific writing & data**

- [**texmark**](https://perrette.github.io/texmark/) — write scientific articles in Markdown and convert them to journal-ready LaTeX/PDF.
- [**papers**](https://perrette.github.io/papers/) — command-line BibTeX bibliography and PDF library manager.
- [**datamanifest**](https://perrette.github.io/datamanifest/) — declarative, reproducible dataset management. *(See also the [datamanifest.toml](https://perrette.github.io/datamanifest.toml/) format spec and the [DataManifest.jl](https://awi-esc.github.io/DataManifest.jl/) Julia port.)*

**Voice helpers** — handy for dictating and proofreading drafts by ear

- [**scribe**](https://perrette.github.io/scribe/) — speech-to-text dictation (Whisper).
- [**bard**](https://perrette.github.io/bard/) — text-to-speech reader (Kokoro / Piper).

## Acknowledgements

The player was devised in conversation with Mistral's Le Chat and OpenAI's
ChatGPT, and my own experience with `pystray` on
[scribe](https://github.com/perrette/scribe).
