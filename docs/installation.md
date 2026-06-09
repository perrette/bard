# Installation

## System dependencies

Install the libraries or system-specific dependencies first:

```bash
sudo apt-get install portaudio19-dev xclip #  portaudio19-dev becomes portaudio with Homebrew
sudo apt install libcairo-dev libgirepository1.0-dev gir1.2-appindicator3-0.1  # Ubuntu ONLY (not needed on MacOS)
pip install PyGObject # Ubuntu ONLY (not needed on MacOS)
```

## Install the app

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

See [Backends & voices](backends.md) for how to download the model files that
the local backends (Kokoro, Piper) need.

## GNOME launcher

On GNOME desktop you can subsequently run:

```bash
bard-install [...]
```

to produce a `.desktop` file for GNOME's quick-launch
(the `[...]` indicates any argument that `bard` takes).
API keys are read from the environment (`OPENAI_API_KEY`, `ELEVENLABS_API_KEY`)
and inherited by the launched process.
