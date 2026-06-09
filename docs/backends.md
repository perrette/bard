# Backends & voices

Bard supports four TTS backends. Use `--backend <name>` to select one at
startup:

| Backend | `--backend` value | Type | Notes |
|---------|------------------|------|-------|
| OpenAI TTS | `openai` | remote | requires `OPENAI_API_KEY` |
| ElevenLabs | `elevenlabs` | remote | requires `ELEVENLABS_API_KEY` |
| Kokoro | `kokoro` | local | free, offline, multilingual (54 voices, 9 languages) |
| Piper | `piper` | local | free, offline, multilingual |

```bash
bard --backend kokoro --voice af_heart
bard --backend piper --voice en_US-amy-medium
bard --backend elevenlabs --voice Rachel
```

## Installing local backend models

Remote backends (`openai`, `elevenlabs`) only need an API key.

Local backends (`kokoro`, `piper`) need model files on disk. Bard searches, in
order: `~/.local/share/{piper,kokoro}/`, then `~/.local/share/bard/{piper,kokoro}/`,
then the system XDG data dirs, then the legacy `~/.cache/bard/{piper,kokoro}/`.
Setting `BARD_PIPER_MODEL`, `BARD_KOKORO_MODEL_PATH`, or `BARD_KOKORO_VOICES_PATH`
overrides the search.

### Piper

Use the downloader that ships with `piper-tts`:

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

### Kokoro

The upstream package has no downloader, so fetch the two files directly:

```bash
mkdir -p ~/.local/share/kokoro
curl -L -o ~/.local/share/kokoro/kokoro-v1.0.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o ~/.local/share/kokoro/voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

`bard --list-backends` shows the install command for any local backend whose
model files are missing.

## Listing backends and voices

```bash
# Show all registered backends with availability:
bard --list-backends

# List voice IDs for the selected backend:
bard --backend openai --list-voices

# Full metadata table (id / language / gender / model), grouped by language:
bard --backend kokoro --list-voices --verbose
```

## Picking a voice by language

Instead of remembering a voice id, you can let bard pick the first one matching a
language tag. Useful with multilingual backends like Kokoro:

```bash
bard --backend kokoro --language fr      # first French voice
bard --backend kokoro --language pt-BR   # first Brazilian-Portuguese voice
```

`--language` is ignored when `--voice` is also set. The tray and terminal
`Voice` submenus also group entries by language for easier browsing.
