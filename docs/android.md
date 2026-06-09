# Android

I was able to install bard on Android via the excellent
[Termux](https://termux.dev) emulator. Not everything works: the tray system app
does not work, the clipboard option only partially works (**only plain text is
copied**). However I could obtain a decent workflow via:

```bash
bard --no-tray --clipboard
```

and using the external player when controls are needed (nice key-driven
in-terminal space for pause etc).

For paywalled articles, I ended up opening them in Firefox, accessing the
Reading mode (excellent, though sometimes the icon is hidden in the URL bar),
selecting all text, copying, and running the above command (for free articles
just copy paste the URL). This requires the Termux API `pkg install
termux-api`.
