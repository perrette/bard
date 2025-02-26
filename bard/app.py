import sys

from bard.models import OpenaiAPI
from bard.audio import AudioPlayer
from bard.util import clean_cache, get_audio_files_from_cache, logger
from bard.input import read_text_from_pdf, preprocess_input_text, get_text_from_clipboard

def get_model(voice=None, model=None, output_format="mp3", openai_api_key=None, backend="openaiapi", chunk_size=None):
    if backend == "openaiapi":
        return OpenaiAPI(voice=voice, model=model, output_format=output_format, api_key=openai_api_key, max_length=chunk_size)
    else:
        raise ValueError(f"Unsupported backend: {backend}")

def main():
    import argparse
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group("API Backend")
    group.add_argument("--voice", default=None, help="Voice to use")
    group.add_argument("--model", default=None, help="Model to use")
    group.add_argument("--output-format", default="mp3", help="Output format")
    group.add_argument("--openai-api-key", default=None, help="OpenAI API key")
    group.add_argument("--backend", default="openaiapi", help="Backend to use")
    group.add_argument("--chunk-size", default=500, type=int, help="Max number of characters sent in one request")

    group = parser.add_argument_group("Frontend")
    group.add_argument("--frontend", choices=["tray", "terminal"], default="tray", help="Frontend to use")
    group.add_argument("--no-tray", action="store_const", dest="frontend", const="terminal", help="Alias for `--frontend terminal`")
    group.add_argument("--no-prompt", action="store_true", help="No prompt. Also assumes `--frontend terminal`")

    group = parser.add_argument_group("Player")
    group.add_argument("--jump-back", type=int, default=15, help="Jump back time in seconds")
    group.add_argument("--jump-forward", type=int, default=15, help="Jump forward time in seconds")
    group.add_argument("--open-external", action="store_true")
    group.add_argument("--external-player", help="Specify the external player to use. Default is `mpv` if installed, otherwise `xdg-open` or `termux-open`.")

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

    model = get_model(voice=o.voice, model=o.model, output_format=o.output_format, openai_api_key=o.openai_api_key, backend=o.backend, chunk_size=o.chunk_size)

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
        o.audio_file = get_audio_files_from_cache()

    if o.audio_file:
        player = AudioPlayer.from_files(o.audio_file)

    elif o.text:
        player = AudioPlayer.from_files(model.text_to_audio_files(o.text))

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
    if o.frontend == "tray":
        from bard.frontends.trayicon import create_app
    else:
        from bard.frontends.terminal import create_app

    app = create_app(model, player, jump_back=o.jump_back, jump_forward=o.jump_forward,
                    clean_cache_on_exit=o.clean_cache_on_exit, external_player=o.external_player)

    if player is not None:
        player.play()

    app.run()

if __name__ == "__main__":
    main()