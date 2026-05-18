import os
import subprocess as sp
from typing import Callable
from desktop_ai_core.frontends import AbstractFrontendApp
from bard.util import logger, clean_cache, get_audio_files_from_cache, is_running_in_termux, get_cache_path, is_parent_directory, CACHE_DIR
from bard.chunking import render_chunks
from bard.input import preprocess_input_text, get_text_from_clipboard
from bard.audio import AudioPlayer
from bard.backends import get_backend

def is_running_in_terminal(view):
    return view is None or getattr(view, "backend", None) == "terminal"

class AbstractApp(AbstractFrontendApp):

    def __init__(self, backend, audioplayer, params=None, models=None, view=None, logger=logger, track_index=None, backend_kwargs=None, api_keys=None, error_callback: Callable[[str, str], None] | None = None):
        super().__init__(params=params, view=view, logger=logger, error_callback=error_callback)
        self.backend = backend
        self.audioplayer = audioplayer
        self.models = models or []
        self.track_index = track_index
        self.is_externally_open = False
        self.backend_kwargs = backend_kwargs or {}
        self.api_keys = api_keys or {}

    def switch_backend(self, name: str) -> bool:
        try:
            kwargs = dict(self.backend_kwargs)
            if self.api_keys.get(name):
                kwargs["api_key"] = self.api_keys[name]
            new_backend = get_backend(name, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to switch backend to {name!r}: {e}")
            return False
        self.backend = new_backend
        self.backend.voice = self.backend.default_voice
        return True

    def set_voice(self, voice_id: str) -> None:
        self.backend.voice = voice_id

    def set_model(self, model_id: str) -> None:
        self.backend.model = model_id

    def is_processed(self, item=None):
        return self.audioplayer is not None

    def show_pause(self, item):
        if not self.is_processed(item):
            return False
        return self.audioplayer.is_playing

    def show_play(self, item):
        if not self.is_processed(item):
            return False
        return not self.audioplayer.is_playing and not self.audioplayer.is_done

    def set_audioplayer(self, view, player):
        view._player = self.audioplayer = player
        if player is not None:
            self.audioplayer.on_done(lambda x: view.update_menu())
            if hasattr(view, 'update_progress'):
                self.audioplayer.on_cursor_update(lambda player: view.update_progress(player))
            if hasattr(view, 'update_state'):
                self.audioplayer.on_file_arrived(lambda p: view.update_state(p))
        view._app = self

    def callback_process_clipboard(self, view, item=None):
        self.logger.info('Processing clipboard...')
        text = get_text_from_clipboard()
        self.logger.info(f'{len(text)} characters copied')
        text = preprocess_input_text(text)

        # clean-up the audio
        if self.audioplayer is not None:
            self.audioplayer.stop()
            self.audioplayer = None
        try:
            chunk_size = self.params.get('chunk_size', 500)
            player = AudioPlayer.from_files(render_chunks(self.backend, text, chunk_size, CACHE_DIR))
            self.set_audioplayer(view, player)
            if self.get_param("play_on_processed"):
                player.play()  # play immediately after the first chunk arrives
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            self.notify_error("Synthesis error", f"{type(exc).__name__}: {exc}")
        finally:
            view.update_menu()

    def callback_previous_track(self, view, item=None):
        self.logger.info('Previous track...')
        if self.audioplayer is not None:
            is_playing = self.audioplayer.is_playing
            self.audioplayer.stop()
        else:
            is_playing = False
        self.audioplayer = None
        if self.track_index is None:
            self.track_index = -1
        elif self.track_index == 0:
            logger.info('Already at the first track')
            return # Do nothing
        else:
            self.track_index -= 1
        try:
            files = get_audio_files_from_cache(self.track_index)
            player = AudioPlayer.from_files(files)
            if is_playing:
                player.play()
            self.set_audioplayer(view, player)
        finally:
            view.update_menu()

    def callback_next_track(self, view, item=None):
        self.logger.info('Next track...')
        if self.audioplayer is not None:
            is_playing = self.audioplayer.is_playing
            self.audioplayer.stop()
        else:
            is_playing = False
        self.audioplayer = None
        if self.track_index is None:
            self.track_index = -1
        elif self.track_index == -1:
            logger.info('Already at the last track')
            return # Do nothing
        else:
            self.track_index += 1
        try:
            files = get_audio_files_from_cache(self.track_index)
            player = AudioPlayer.from_files(files)
            if is_playing:
                player.play()
            self.set_audioplayer(view, player)
        finally:
            view.update_menu()

    def callback_delete_this_track(self, view, item):
        if self.audioplayer is None:
            return
        self.audioplayer.stop()
        for f in self.audioplayer.filepaths:
            if not os.path.exists(f):
                logger.warning(f"Skipping {f} (file not found)")
                continue
            # only delete files in the CACHE folder
            if not is_parent_directory(get_cache_path(""), f):
                logger.warning(f"Skipping {f} (outside of cache folder)")
                continue
            logger.warning(f"Deleting {f}")
            os.remove(f)
        self.track_index = None
        self.set_audioplayer(view, None)

    def callback_play(self, view, item=None):
        if self.audioplayer is None:
            self.logger.error('No audio to play')
            return
        self.logger.info('Playing...')
        self.audioplayer.on_done(lambda x: view.update_menu()).play()
        self.logger.info('Exiting callback...')

    def callback_pause(self, view, item=None):
        self.logger.info('Pausing...')
        self.audioplayer.pause()

    def callback_stop(self, view, item=None):
        self.logger.info('Stopping...')
        self.audioplayer.stop()

    def callback_jump_back(self, view, item=None):
        self.logger.info('Jumping back...')
        position = self.audioplayer.current_position / self.audioplayer.fs
        print("current_position", self.audioplayer.current_position, "fs", "or", position, "seconds")
        print("jumping to", position - self.get_param("jump_back"), "(seconds)")
        self.audioplayer.jump_to(position - self.get_param("jump_back"))

    def callback_jump_forward(self, view, item=None):
        self.logger.info('Jumping forward...')
        position = self.audioplayer.current_position / self.audioplayer.fs
        print("current_position", self.audioplayer.current_position, "fs", "or", position, "seconds")
        print("jumping to", position + self.get_param("jump_forward"), "(seconds)")
        self.audioplayer.jump_to(position + self.get_param("jump_forward"))

    def callback_quit(self, view, item=None):
        self.logger.info('Quitting...')
        view.stop()
        if self.audioplayer is not None:
            self.audioplayer.stop()
        if self.get_param("clean_cache_on_exit"):
            clean_cache()

    def callback_open_external(self, view, item=None):
        self.logger.info('Opening with external player...')
        if self.audioplayer is None:
            self.logger.error('No audio to play')
            return
        player = self.audioplayer
        external_player = self.get_param("external_player")
        self.is_externally_open = True
        try:
            player.open_external(external_player, terminal=is_running_in_terminal(view), termux=is_running_in_termux())
        except KeyboardInterrupt:
            logger.info("External player interrupted")
        finally:
            self.is_externally_open = False
