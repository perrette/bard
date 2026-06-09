# Input sources

You can do a one-off reading by indicating the source content with one of the
following:

```bash
bard --text "Hello world, how are you today"
bard --clipboard
bard --url "example.com" # also accepts file://
bard --html-file /path/to/downloaded.html # access a page with paywall, download it, feed it to bard
bard --pdf-file /path/to/document.pdf  # careful if you pay for it... (the full thing will be transcribed even if you listen to a small bit of it)
bard --audio-file /path/to/audio.mp3 # no actual request, only useful for testing the audio player
```

The above command will still launch the system tray icon, and so provide access
to the audio player's (basic) controls.

## Clipboard parsing

The clipboard parsing capabilities are elaborate enough so that it can detect an
URL, a file path or common HTML markup. If a file path is detected, the
extension is checked for `.html`-ish and `.pdf`, and the data is extracted
accordingly. Here we make good use of the most useful work on
[readability](https://pypi.org/project/readability-lxml).

In particular, this allows relatively easy reading out of webpages behind
paywalls, by right-clicking on "View Page Source" (or download the html file if
the source doesn't contain the text), select all text, copy and just proceed
with bard's "Process Copied Text" or `--clipboard` options. For other articles
not protected by a paywall, copying the URL should suffice.

## Resume and cleanup

You can resume the previous recording (the audio won't play right away in this
case, but you can use the reader):

```bash
bard --resume
```

You can also ask the app to remove your (local) traces:

```bash
bard --clean-cache-on-exit
```
