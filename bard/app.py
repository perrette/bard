import os
import sys
import argparse

from bard.backends import get_backend, available_backends, probe_backend, BACKENDS
from bard.audio import AudioPlayer
from bard.chunking import render_chunks, render_to_file
from bard.cache import get_resume_files
from bard.util import clean_cache, logger, CACHE_DIR
from bard.input import read_text_from_pdf, preprocess_input_text, get_text_from_clipboard


class _NoInteractiveAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=0, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == "--no-prompt":
            print("warning: --no-prompt is deprecated; use --no-interactive instead", file=sys.stderr)
        setattr(namespace, self.dest, False)


def main():
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group("Backend")
    group.add_argument("--voice", default=None, help="Voice to use")
    group.add_argument("--language", default=None, help="Pick the first voice for the given language tag (e.g. 'fr' or 'fr-FR'). Ignored if --voice is also set.")
    group.add_argument("--model", default=None, help="Model to use")
    group.add_argument("--output-format", default=None, help="Output format (default: mp3, or inferred from --output-file extension)")
    group.add_argument("--backend", default="openai", help="Backend to use")
    group.add_argument("--chunk-size", default=500, type=int, help="Max number of characters sent in one request")
    group.add_argument("--list-voices", action="store_true", help="List available voices for the selected backend and exit")
    group.add_argument("--verbose", action="store_true", help="With --list-voices: show language/gender/model table")
    group.add_argument("--list-backends", action="store_true", help="List registered backends with availability and exit")

    group = parser.add_argument_group("Output")
    group.add_argument("-o", "--output-file", default=None, help="Write the rendered audio to this file and exit. Implies headless (no tray, no terminal UI) and silent unless --play is also given.")
    group.add_argument("--play", action="store_true", help="With --output-file, also play the audio after writing it.")

    group = parser.add_argument_group("Frontend")
    group.add_argument("--frontend", choices=["tray", "terminal"], default="tray", help="Frontend to use")
    group.add_argument("--no-tray", action="store_const", dest="frontend", const="terminal", help="Alias for `--frontend terminal`")
    group.add_argument("--no-interactive", "--no-prompt", dest="interactive", default=True,
                       action=_NoInteractiveAction,
                       help="With --frontend terminal, skip the interactive menu and play immediately. (--no-prompt is a deprecated alias.)")

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
    parser.add_argument("--refresh-cache", action="store_true", help="Clear the API disk cache and exit")

    o = parser.parse_args()

    if o.refresh_cache:
        from bard.backends import diskcache
        from bard import audiocache
        diskcache.clear_all()
        audiocache.clear_all()
        return 0

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

    if o.output_format is None:
        if o.output_file:
            ext = os.path.splitext(o.output_file)[1].lstrip(".").lower()
            o.output_format = ext or "mp3"
        else:
            o.output_format = "mp3"

    backend_kwargs = {
        "output_format": o.output_format,
        "max_length": o.chunk_size,
    }

    voice = o.voice
    if o.language and not voice:
        from bard.voices import find_first_for_language
        # Use the registered class to enumerate voices without paying for
        # full model load -- list_voices_meta() is metadata-only for kokoro
        # and openai; remote backends still need an instance for it.
        cls = BACKENDS[o.backend]
        try:
            metas = cls.__new__(cls).list_voices_meta()
        except Exception:
            metas = None
        if metas:
            picked = find_first_for_language(metas, o.language)
        else:
            picked = None
        if picked is None:
            # Fall back: instantiate and search the live list.
            tmp = get_backend(o.backend, voice=None, model=o.model, **backend_kwargs)
            picked = find_first_for_language(tmp.list_voices_meta(), o.language)
        if picked is None:
            print(f"No voice for language {o.language!r} in backend {o.backend!r}", file=sys.stderr)
            return 2
        voice = picked.id

    backend = get_backend(o.backend, voice=voice, model=o.model, **backend_kwargs)

    if o.list_voices:
        from bard.voices import group_by_language
        groups = group_by_language(backend.list_voices_meta())
        if o.verbose:
            get_desc = getattr(backend, "get_voice_description", None)
            get_cat = getattr(backend, "get_voice_category", None)
            print(f"{'name':<24} {'category':<14} {'language':<10} {'gender':<8} description")
            for lang, vs in groups.items():
                print(f"-- {lang or 'Other'} ({len(vs)}) --")
                for v in vs:
                    name = (v.display or v.id) or ""
                    cat = (get_cat(v.id) if callable(get_cat) else None) or ""
                    gender = v.gender or ""
                    desc = (get_desc(v.id) if callable(get_desc) else None) or ""
                    print(f"{name:<24} {cat:<14} {(lang or ''):<10} {gender:<8} {desc}")
        else:
            for lang, vs in groups.items():
                if len(groups) > 1:
                    print(f"-- {lang or 'Other'} --")
                for v in vs:
                    print(v.display or v.id)
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

    if o.output_file:
        if o.audio_file:
            parser.error("--output-file does not support --audio-file input (use a file copy instead).")
        if not o.text:
            parser.error("--output-file requires text input (--text, --text-file, --pdf-file, --url, --html-file, --clipboard, or --clipboard-text).")
        out_path = render_to_file(backend, o.text, o.chunk_size, o.output_file, cache_dir=CACHE_DIR)
        logger.info(f"Wrote audio to {out_path}")
        if o.play:
            player = AudioPlayer.from_file(out_path)
            try:
                player.play()
                player.wait()
            finally:
                player.stop()
        if o.clean_cache_on_exit:
            clean_cache()
        return 0

    if o.audio_file:
        player = AudioPlayer.from_files(o.audio_file)

    elif o.text:
        player = AudioPlayer.from_files(render_chunks(backend, o.text, o.chunk_size, CACHE_DIR))

    else:
        player = None

    if not o.interactive:
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