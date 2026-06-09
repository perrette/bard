<!--
  Home page. The feature bullets are pulled straight from README.md (single
  source of truth) via the include-markdown plugin; everything else links into
  the guide.
-->
<p align="center">
  <img src="https://github.com/perrette/bard/raw/main/bard_data/share/icon.png" alt="Bard" width="96">
</p>

# Bard

Bard is a text-to-speech client that integrates on the desktop. It reads plain
text, clipboard content, web pages, or PDFs aloud through a system-tray player.

{%
  include-markdown "../README.md"
  start="<!-- intro-start -->"
  end="<!-- intro-end -->"
%}

## Get started

```bash
pip install bard-cli[all]
bard
```

- **[Installation](installation.md)** — system libraries, backend extras, and the GNOME launcher.
- **[Quickstart](quickstart.md)** — your first reading from the clipboard.
- **[Backends & voices](backends.md)** — OpenAI, ElevenLabs, Kokoro, Piper.
- **[Tray menu](tray-menu.md)** — switch backend, model, and voice at runtime.

## Guides

- [Input sources](input-sources.md) — text, clipboard, URLs, HTML, PDF, audio files.
- [Batch render to a file](batch-render.md) — synthesise audio without the player.
- [Backends & voices](backends.md) — installing local models, listing and picking voices.
- [Tray menu](tray-menu.md)
- [Global keyboard shortcut](keyboard-shortcut.md) — drive bard from anywhere via signals.
- [Fine-tuning](fine-tuning.md) — chunk size and request length.
- [Player](player.md)
- [Android](android.md) — running bard under Termux.

## From the same author

A few other open-source tools I maintain.

**Scientific writing & data**

- [**texmark**](https://perrette.github.io/texmark/) — write scientific articles in Markdown and convert them to journal-ready LaTeX/PDF.
- [**papers**](https://perrette.github.io/papers/) — command-line BibTeX bibliography and PDF library manager.
- [**datamanifest**](https://perrette.github.io/datamanifest/) — declarative, reproducible dataset management. *(See also the [datamanifest.toml](https://perrette.github.io/datamanifest.toml/) format spec and the [DataManifest.jl](https://awi-esc.github.io/DataManifest.jl/) Julia port.)*

**Speech to Text (dictate) and Text to Speech (read-aloud) tools**

- [**scribe**](https://perrette.github.io/scribe/) — speech-to-text dictation.
