[![pypi](https://img.shields.io/pypi/v/bard)](https://pypi.org/project/bard)
![](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fperrette%bard%2Frefs%2Fheads%2Fmain%2Fpyproject.toml)

# Bard  <img src="bard_data/share/icon.png" width=48px>

Bard is a text to speech client that integrates on the desktop

Dependencies include:
- `openai`
- `pystray`
- `sounddevice`
- `soundfile`

# Usage

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
bard --default-file /path/to/audio.mp3
```


## Install

### GNOME

On GNOME desktop you can run:
```bash
scribe-install
```
to produce a `.desktop` file for GNOME's quick-launch.