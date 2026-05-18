[![pypi](https://img.shields.io/pypi/v/bard-cli)](https://pypi.org/project/bard-cli)
![](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fperrette%2Fbard%2Frefs%2Fheads%2Fmain%2Fpyproject.toml)
[![tests](https://github.com/perrette/bard/actions/workflows/tests.yml/badge.svg)](https://github.com/perrette/bard/actions/workflows/tests.yml)

# Bard  <img src="https://github.com/perrette/bard/raw/main/bard_data/share/icon.png" width=48px>

Bard is a text to speech client that integrates on the desktop

## Install

Install libraries or system-specific dependencies:

```bash
sudo apt-get install portaudio19-dev xclip #  portaudio19-dev becomes portaudio with Homebrew
sudo apt install libcairo-dev libgirepository1.0-dev gir1.2-appindicator3-0.1  # Ubuntu ONLY (not needed on MacOS)
pip install PyGObject # Ubuntu ONLY (not needed on MacOS)
```

Install the main app with all optional dependencies:

```bash
pip install bard-cli[all]          # OpenAI, ElevenLabs, Kokoro (no Piper)
pip install bard-cli[all-local]    # all of the above + Piper
```

You can also install individual backend extras:

| Extra | Backend | Type |
|-------|---------|------|
| `bard-cli[openai]` | OpenAI TTS | remote (requires `OPENAI_API_KEY`) |
| `bard-cli[elevenlabs]` | ElevenLabs | remote (requires `ELEVENLABS_API_KEY`) |
| `bard-cli[kokoro]` | Kokoro | local, free, offline |
| `bard-cli[piper]` | Piper | local, free, offline |

### GNOME

On GNOME desktop you can subsequently run:
```bash
bard-install [...] --openai-api-key $OPENAI_API_KEY
```
to produce a `.desktop` file for GNOME's quick-launch
(the `[...]` indicates any argument that `bard` takes)

## Usage

In a terminal:

```bash
bard
```
which defaults to:
```bash
bard --backend openai --voice alloy --model tts-1
```
(this assumes the environment variable `OPENAI_API_KEY` is defined)

An icon should show up almost immediately in the system tray, with options to copy the content of the clipboard (the last thing you copy-pasted)
and send that to the AI model for reading aloud.

<img src=https://github.com/user-attachments/assets/a90ccd1c-7431-4554-9d41-0e9c1b4399f2 width=300px>

You can also do a one-off reading by indicating the source content with one of the following:

```bash
bard --text "Hello world, how are you today"
bard --clipboard
bard --url "example.com" # also accepts file://
bard --html-file /path/to/downloaded.html # access a page with paywal, download it, feed it to bard
bard --pdf-file /path/to/document.pdf  # careful if you pay for it... (the full thing will be transcribed even if you listen to a small bit of it)
bard --audio-file /path/to/audio.mp3 # no actual request, only useful for testing the audio player
```
The above command will still launch the system tray icon, and so provide access to the audio player's (basic) controls.
There is also a terminal version via the `--no-tray` parameter, with the same elementary controls as in the system tray.
And for a one-off execution of the program without controls, use `--no-prompt`.

The clipboard parsing capabilities are elaborate enough so that it can detect an URL, a file path or common HTML markup.
If a file path is detected, the extension is checked for `.html`-ish and `.pdf`, and the data is extracted accordingly.
Here we make good use of the most useful work on [readability](https://pypi.org/project/readability-lxml).
In particular, this allows relatively easy reading out of webpages behind paywals, by right-clicking on "View Page Source" (or download the html file if the source doesn't contain the text), select all text, copy and just proceed with bards' "Process Copied Text" or `--clipboard` options.
For other articles not protected by a paywall, copying the URL should suffice.

You can resume the previous recording (the audio won't play right away in this case, but you can use the reader):
```bash
bard --resume
```
You can ask also ask the app to removed your (local) traces:
```bash
bard --clean-cache-on-exit
```

## Backends

Bard supports four TTS backends. Use `--backend <name>` to select one at startup:

| Backend | `--backend` value | Type | Notes |
|---------|------------------|------|-------|
| OpenAI TTS | `openai` | remote | requires `OPENAI_API_KEY` (or `--openai-api-key`) |
| ElevenLabs | `elevenlabs` | remote | requires `ELEVENLABS_API_KEY` (or `--elevenlabs-api-key`) |
| Kokoro | `kokoro` | local | free, offline, English voices |
| Piper | `piper` | local | free, offline, multilingual |

```bash
bard --backend kokoro --voice af_sky
bard --backend piper --voice en_US-amy-medium
bard --backend elevenlabs --voice Rachel
```

### Installing local backend models

Remote backends (`openai`, `elevenlabs`) only need an API key.

Local backends (`kokoro`, `piper`) need model files on disk. Bard searches, in
order: `~/.local/share/{piper,kokoro}/`, then `~/.local/share/bard/{piper,kokoro}/`,
then the system XDG data dirs, then the legacy `~/.cache/bard/{piper,kokoro}/`.
Setting `BARD_PIPER_MODEL`, `BARD_KOKORO_MODEL_PATH`, or `BARD_KOKORO_VOICES_PATH`
overrides the search.

**Piper** — use the downloader that ships with `piper-tts`:

```bash
python -m piper.download_voices en_US-amy-medium --data-dir ~/.local/share/piper
```

Voice catalog: <https://huggingface.co/rhasspy/piper-voices>. Any `.onnx` files
in the chosen directory show up under the `Voice` submenu and in
`bard --backend piper --list-voices`.

For community voices outside the official catalog (e.g. extra French voices
hosted on HuggingFace under other users), `python -m piper.download_voices`
will 404 — fetch the two files directly. Each Piper voice is one `.onnx`
plus its sibling `.onnx.json`:

```bash
cd ~/.local/share/piper
HF=https://huggingface.co/csukuangfj/vits-piper-fr_FR-miro-high/resolve/main
curl -LO $HF/fr_FR-miro-high.onnx
curl -LO $HF/fr_FR-miro-high.onnx.json
```

Voice switching at runtime only sees `.onnx` files sibling to the currently
loaded voice, so keep all voices in the same directory.

**Kokoro** — the upstream package has no downloader, so fetch the two files
directly:

```bash
mkdir -p ~/.local/share/kokoro
curl -L -o ~/.local/share/kokoro/kokoro-v0_19.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx
curl -L -o ~/.local/share/kokoro/voices.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin
```

`bard --list-backends` shows the install command for any local backend whose
model files are missing.

### Listing backends and voices

```bash
# Show all registered backends with availability:
bard --list-backends

# List voice IDs for the selected backend:
bard --backend openai --list-voices

# Full metadata table (id / language / gender / model):
bard --backend openai --list-voices --verbose
```

## Tray menu

The system tray icon exposes a `TTS` submenu with three sub-submenus:

```
TTS ▸
  Backend ▸  ● openai      (remote)
             ○ elevenlabs  (remote)   ← greyed if API key absent
             ○ kokoro      (local)    ← greyed if not installed
             ○ piper       (local)    ← greyed if model file absent
  Model   ▸  ● tts-1
             ○ tts-1-hd
             ○ gpt-4o-mini-tts
  Voice   ▸  🇺🇸 alloy
             🇺🇸 echo (M)
             🇺🇸 nova (F)
             ...
```

Backend and voice can be switched at runtime without restarting. The `Options`
submenu retains its non-TTS controls (auto-play, jump interval, etc.).

## Fine-tuning

```bash
bard --chunk-size 500  # that's the default
```
sets the maximum length (in characters) of a request. That means about 30 seconds of speech.
The program will split up the text in chunks (according to the punctuation) and download them sequentially.
The reading will start with the first chunk, that's why it is convenient to keep it small.
You can set that smaller or up to the maximum allowed by the backend (4096 for OpenAI).

## Player

The player was devised in conversation with Mistral's Le Chat and Open AI's Chat GPT, and my own experience with `pystray` on [scribe](https://github.com/perrette/scribe). It works.
I'm open for suggestion for other, platform-independent integrations to the OS.
TODO: I want to add a functioning "Open with external reader" option. At the moment it is experimental and only accounts for the first file.

## Android

I was able to install bard on Android via the excellent [Termux](https://termux.dev) emulator. Not everything works: the tray system app does not work, the clipboard option only partially works (**only plain text is copied**). However I could obtain a decent workflow for one-off reading (no player controls) via:
```bash
bard --no-tray --clipboard
```
For paywalled articles, I ended up opening them in Firefox, acessing the Reading mode (excellent, though sometimes the icon is hidden in the URL bar), selecting all text, copying, and running the above command (for free articles just copy paste the URL). This requires the termux API `pkg install termux-api`.
