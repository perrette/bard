from bard.util import logger, clean_cache, get_audio_files_from_cache
from bard.input import preprocess_input_text, get_text_from_clipboard
from bard.audio import AudioPlayer

class AbstractApp:

    def __init__(self, model, audioplayer, params=None, models=None, view=None, logger=logger):
        self.model = model
        self.audioplayer = audioplayer
        self.params = params or {}
        self.models = models or []
        self.view = view
        self.logger = logger

    def set_param(self, name, value):
        self.params[name] = value

    def get_param(self, name):
        return self.params.get(name)

    def checked(self, item):
        return self.get_param(str(item))

    def is_processed(self, item):
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
        self.audioplayer.on_done(lambda x: view.update_menu()).play()
        self.audioplayer.on_cursor_update(lambda player: view.show_progress(player))
        view._app = self

    def callback_process_clipboard(self, view, item):
        self.logger.info('Processing clipboard...')
        text = get_text_from_clipboard()
        self.logger.info(f'{len(text)} characters copied')
        text = preprocess_input_text(text)

        # clean-up the audio
        if self.audioplayer is not None:
            self.audioplayer.stop()
            self.audioplayer = None
        try:
            player = AudioPlayer.from_files(self.model.text_to_audio_files(text))
            self.set_audioplayer(view, player)
            # self.logger.info('Done!')
        finally:
            view.update_menu()

    def callback_previous_track(self, view, item=None):
        self.logger.info('Previous track...')
        self.audioplayer = None
        try:
            files = get_audio_files_from_cache()
            player = AudioPlayer.from_files(files)
            self.set_audioplayer(view, player)
        finally:
            view.update_menu()

    def callback_play(self, view, item):
        if self.audioplayer is None:
            self.logger.error('No audio to play')
            return
        self.logger.info('Playing...')
        self.audioplayer.on_done(lambda x: view.update_menu()).play()
        self.logger.info('Exiting callback...')

    def callback_pause(self, view, item):
        self.logger.info('Pausing...')
        self.audioplayer.pause()

    def callback_stop(self, view, item):
        self.logger.info('Stopping...')
        self.audioplayer.stop()

    def callback_jump_back(self, view, item):
        self.logger.info('Jumping back...')
        position = self.audioplayer.current_position / self.audioplayer.fs
        print("current_position", self.audioplayer.current_position, "fs", "or", position, "seconds")
        print("jumping to", position - self.get_param("jump_back"), "(seconds)")
        self.audioplayer.jump_to(position - self.get_param("jump_back"))

    def callback_jump_forward(self, view, item):
        self.logger.info('Jumping forward...')
        position = self.audioplayer.current_position / self.audioplayer.fs
        print("current_position", self.audioplayer.current_position, "fs", "or", position, "seconds")
        print("jumping to", position + self.get_param("jump_forward"), "(seconds)")
        self.audioplayer.jump_to(position + self.get_param("jump_forward"))

    def callback_quit(self, view, item):
        self.logger.info('Quitting...')
        view.stop()
        if self.audioplayer is not None:
            self.audioplayer.stop()
        if self.get_param("clean_cache_on_exit"):
            clean_cache()

    def callback_toggle_option(self, view, item):
        self.set_param(str(item), not self.get_param(str(item)))

    def callback_open_external(self, view, item):
        self.logger.info('Opening with external player...')
        if self.audioplayer is None:
            self.logger.error('No audio to play')
            return
        self.audioplayer.open_external(self.get_params("external_player"))