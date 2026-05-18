import sys

from bard.backends import get_backend, available_backends, probe_backend, BACKENDS
from bard.audio import AudioPlayer
from bard.chunking import render_chunks
from bard.cache import get_resume_files
from bard.util import clean_cache, logger, CACHE_DIR
from bard.input import read_text_from_pdf, preprocess_input_text, get_text_from_clipboard

def main():
    import argparse
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group("API Backend")
    group.add_argument("--voice", default=None, help="Voice to use")
    group.add_argument("--model", default=None, help="Model to use")
    group.add_argument("--output-format", default="mp3", help="Output format")
    group.add_argument("--openai-api-key", default=None, help="OpenAI API key")
    group.add_argument("--backend", default="openai", help="Backend to use")
    group.add_argument("--chunk-size", default=500, type=int, help="Max number of characters sent in one request")
    group.add_argument("--list-voices", action="store_true", help="List available voices for the selected backend and exit")
    group.add_argument("--verbose", action="store_true", help="With --list-voices: show language/gender/model table")
    group.add_argument("--list-backends", action="store_true", help="List registered backends with availability and exit")

    group = parser.add_argument_group("Frontend")
    group.add_argument("--frontend", choices=["tray", "terminal"], default="tray", help="Frontend to use")
    group.add_argument("--no-tray", action="store_const", dest="frontend", const="terminal", help="Alias for `--frontend terminal`")
    group.add_argument("--no-prompt", action="store_true", help="No prompt. Also assumes `--frontend terminal`")

    group = parser.add_argument_group("Player")
    group.add_argument("--jump-back", type=int, default=15, help="Jump back time in seconds")
    group.add_argument("--jump-forward", type=int, default=15, help="Jump forward time in seconds")
    group.add_argument("--open-external", action="store_true")
    group.add_argument("--external-player", help="Specify the external player to use. Default is `mpv` if installed, otherwise `xdg-open` or `termux-open`.")
    group.add_argument("--no-play-on-processed", action="store_false", dest="play_on_processed", help="Do not play immediately after the text has been processed (e.g. for use with external players).")
    group.add_argument("--play-on-processed", action="store_true", help="Play immediately after the text has been processed. Default is True.")

    group = parser.add_argument_group("Kick-start")
    group = group.add_mutually_exclusive_group()
    group.add_argument("--text", help="Text to speak right away")
    group.add_argument("--clipboard-text", help="The content of the copied clipboard, which is parsed for URL etc")
    group.add_argument("--clipboard", help="Past text from clipboard to speak right away", action="store_true")
    group.add_argument("--text-file", help="Text file to read along.")
    group.add_argument("--html-file", help="HTML file to read along.")
    group.add_argument("--url", help="URL to fetch and read along.")
    group.add_argument("--pdf-file", help="PDF File to read along (pdf2text from poppler is used).")
    group.add_argument("--audio-file", nargs="+", help="audio file(s) to play right away")
    group.add_argument("--resume", action="store_true", help="Resume the last played file (if the cache is not cleaned)")

    group = parser.add_argument_group("Maintenance")
    parser.add_argument("--clean-cache-on-exit", action="store_true", help="Clean the cache directory on exit")

    o = parser.parse_args()

    if o.list_backends:
        for name in available_backends():
            cls = BACKENDS[name]
            locality = "local" if cls.is_local else "remote"
            ok, reason = probe_backend(name)
            status = "ok" if ok else f"missing: {reason}"
            print(f"{name}\t{locality}\t{status}")
            if not ok and cls.install_hint and "not found" in (reason or ""):
                print(f"    install: {cls.install_hint}")
        return 0

    backend_kwargs = {
        "api_key": o.openai_api_key,
        "output_format": o.output_format,
        "max_length": o.chunk_size,
    }

    backend = get_backend(o.backend, voice=o.voice, model=o.model, **backend_kwargs)

    if o.list_voices:
        if o.verbose:
            model_col = o.model or backend.default_model or ""
            print(f"{'id':<30} {'language':<12} {'gender':<8} {'model'}")
            for v in backend.list_voices_meta():
                lang = v.language or ""
                gender = v.gender or ""
                print(f"{v.id:<30} {lang:<12} {gender:<8} {model_col}")
        else:
            for voice in backend.list_voices():
                print(voice)
        return 0

    if o.url:
        from bard.input import extract_text_from_url
        o.text = extract_text_from_url(o.url)

    elif o.html_file:
        from bard.html import extract_text_from_html
        o.text = extract_text_from_html(open(o.html_file).read())

    elif o.text_file:
        with open(o.text_file) as f:
            o.text = f.read()

    elif o.clipboard_text:
        o.text = preprocess_input_text(o.clipboard_text)

    elif o.clipboard:
        clipboard = get_text_from_clipboard()
        o.text = preprocess_input_text(clipboard)

    elif o.pdf_file:
        o.text = read_text_from_pdf(o.pdf_file)

    elif o.resume:
        o.audio_file = get_resume_files()

    if o.audio_file:
        player = AudioPlayer.from_files(o.audio_file)

    elif o.text:
        player = AudioPlayer.from_files(render_chunks(backend, o.text, o.chunk_size, CACHE_DIR))

    else:
        player = None

    if o.no_prompt:
        if player is None:
            parser.error("No files or text provided to play. Exiting...")
            sys.exit(1)

        if o.open_external:
            try:
                player.wait()
            except KeyboardInterrupt:
                logger.info("Download Interrupted by user. Proceeding to play the downloaded files.")
            finally:
                player.stop()
            player.open_external(o.external_player)

        else:
            try:
                player.play()
                player.wait()

            finally:
                player.stop()

        if o.clean_cache_on_exit:
            clean_cache()

        return 0

    # APP
    options = {
        "clean_cache_on_exit": o.clean_cache_on_exit,
        "external_player": o.external_player,
        "play_on_processed": o.play_on_processed,
        "chunk_size": o.chunk_size,
    }

    if o.frontend == "tray":
        from bard.frontends.trayicon import create_app
    else:
        from bard.frontends.terminal import create_app

    app = create_app(backend, player, jump_back=o.jump_back, jump_forward=o.jump_forward, backend_kwargs=backend_kwargs, **options)

    if player is not None:
        player.play()

    app.run()

if __name__ == "__main__":
    main()