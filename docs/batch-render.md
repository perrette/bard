# Batch render to a file

To render text to an audio file without launching the player, pass
`-o/--output-file`:

```bash
bard --text "Hello world" -o hello.mp3       # silent, just writes the file
bard --pdf-file paper.pdf -o paper.wav       # PDF → WAV, no playback
bard --text "Hello" -o hello.mp3 --play      # write the file AND play it
```

With `-o` no tray icon or terminal UI is launched: bard synthesises the text,
writes the concatenated audio to the given path, and exits. The output format is
inferred from the file extension when `--output-format` isn't given.
