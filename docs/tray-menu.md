# Tray menu

The system tray icon shows the active `Vendor model` as the top-level TTS entry,
with `Model` and `Voice` sub-submenus inside. Selecting a model also switches
backend if needed:

```
OpenAI gpt-4o-mini-tts ▸
  Model ▸  OpenAI (remote)     ▸  ● gpt-4o-mini-tts
                                  ○ tts-1
                                  ○ tts-1-hd
           Kokoro (local)      ▸  …                ← greyed if not installed
           ElevenLabs (remote) ▸  …                ← greyed if API key absent
           Piper (local)          ← single radio (one model per file) — greyed if absent
  Voice ▸  ● alloy
           ○ echo (M)
           ○ nova (F)
           ...
```

For multilingual backends (Kokoro, Piper, ElevenLabs) the `Voice` submenu groups
voices by language with a flag prefix on each group header, e.g. `🇺🇸 en (24)`,
`🇫🇷 fr (3)`.

Backend, model, and voice can all be switched at runtime without restarting. The
`Options` submenu retains its non-TTS controls (auto-play, jump interval, etc.).
