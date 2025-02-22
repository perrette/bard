[![pypi](https://img.shields.io/pypi/v/bard-cli)](https://pypi.org/project/bard-cli)
![](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fperrette%2Fbard%2Frefs%2Fheads%2Fmain%2Fpyproject.toml)

# Bard  <img src="https://github.com/perrette/bard/raw/main/bard_data/share/icon.png" width=48px>

Bard is a text to speech client that integrates on the desktop

## Install

Install libraries or system-specific dependencies:

```bash
sudo apt-get install portaudio19-dev xclip #  portaudio19-dev becomes portaudio with Homebrew
sudo apt install libcairo-dev libgirepository1.0-dev gir1.2-appindicator3-0.1  # Ubuntu ONLY (not needed on MacOS)
pip install PyGObject # Ubuntu ONLY (not needed on MacOS)
```

Install the main app

```bash
pip install bard-cli
```

Install optional dependencies
```bash
pip install openai
```
(at the moment openai is the only backend so you better have it installed ;))


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
bard --backend openaiapi --voice allow --model tts-1
```
(this assumes the environment variable `OPENAI_API_KEY` is defined)

An icon should show up almost immediately in the system tray, with options to copy the content of the clipboard (the last thing you copy-pasted)
and send that to the AI model for reading aloud.

<img src=https://github.com/user-attachments/assets/a90ccd1c-7431-4554-9d41-0e9c1b4399f2 width=300px>

For testing you can also start the app with

```bash
bard --audio-file /path/to/audio.mp3
```
and then the actual API:

```bash
bard --text "Hello world, how are you today"
```

You can resume the previous recording (the app won't play right away in this case):
```bash
bard --resume
```

You can ask also ask the app to removed your (local) traces:
```bash
bard --clean-cache-on-exit
```

## Fine-tuning

```bash
bard --chunk-size 500  # that's the default
```
sets the maximum length (in characters) of a request. That means about 30 seconds of speech.
The program will split up the text in chunks (according to the punctuation) and download them sequentially.
The reading will start with the first chunk, that's why it is convenient to keep it small.
You can set that smaller or up to the maximum allowed by the openai API (4096).

## Player

The player was devised in conversation with Mistral's Le Chat and Open AI's Chat GPT, and my own experience with `pystray` on [scribe](https://github.com/perrette/scribe). It works.

I'm open for suggestion for other, platform-independent integrations to the OS.


## Roadmap

Include more backends including local ones.

## Hint

To read whole web pages check out the excellent [unclutter](https://unclutter.it) browser extensions (reading mode).
