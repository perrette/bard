"""Based on a conversation with Chat GPT...
"""
import sounddevice as sd
import soundfile as sf
import threading
import os
import subprocess as sp
import numpy as np
import time
from bard.util import logger, get_cache_path

def read_audio_with_pydub(filename):
    from pydub import AudioSegment
    audio = AudioSegment.from_mp3(filename)

    # Convert to numpy float32 array in range [-1, 1]
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)

    # Handle stereo by reshaping (pydub uses interleaved samples for stereo)
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))

    # Normalize to range [-1, 1] (16-bit PCM)
    samples /= 2**15
    return samples, audio.frame_rate


def read_audio(filename):
    try:
        data, fs = sf.read(filename, dtype='float32')  # Load file into memory
    except sf.LibsndfileError:
        data, fs = read_audio_with_pydub(filename)
    return data, fs


class AudioPlayer:
    def __init__(self, data, fs, filepaths=None):
        if data.ndim == 1:
            data = data[:, np.newaxis]
        # Add 0.5 seconds of silence before the data
        silence = np.zeros((int(0.5 * fs), data.shape[1]), dtype=np.float32)
        data = np.concatenate([silence, data], axis=0)
        self.data, self.fs = data, fs
        self.stream = None
        self.play_thread = None
        self.current_position = 0  # Track position in samples
        self.is_playing = False
        self.is_stopped = False  # Track if we should reset position
        self.is_streaming = False
        self.lock = threading.Lock()
        self._done_callback = None
        self._playing_callback = None
        self._position_callback = None
        self._callback_on_file_arrived = None
        self._callback_on_data_arrived = None
        self.filepaths = [str(f) for f in filepaths] or []

    @classmethod
    def from_file(cls, filename):
        logger.info(f"Loading file: {filename}")
        data, fs = read_audio(filename)
        return cls(data, fs, filepaths=[filename])

    def on_done(self, callback):
        self._done_callback = callback
        return self

    def on_playing(self, callback):
        with self.lock:
            self._playing_callback = callback
        return self

    def on_cursor_update(self, callback):
        with self.lock:
            self._position_callback = callback
        return self

    def on_file_arrived(self, callback):
        with self.lock:
            self._callback_on_file_arrived = callback
        return self

    def on_data_arrived(self, callback):
        with self.lock:
            self._callback_on_data_arrived = callback
        return self

    @property
    def is_done(self):
        """ Returns True if playback has finished, False otherwise """
        return self.current_position >= len(self.data)

    def _callback(self, outdata, frames, time, status):
        """ Sounddevice callback function to stream audio """
        if status:
            print(status, flush=True)
        with self.lock:
            if not self.is_playing:
                outdata[:] = np.zeros((frames, self.data.shape[1]))  # Output silence
                return
            end = self.current_position + frames
            if end > len(self.data):
                end = len(self.data)
                self.is_playing = False  # Auto-pause at end of track
            outdata[:end - self.current_position] = self.data[self.current_position:end]
            self.current_position = end  # Update position

    def play(self):
        """ Start or resume playback """
        with self.lock:
            if self.is_playing:
                return  # Already playing
            self.is_playing = True
            self.is_stopped = False  # Don't reset position

        if self.stream is None:
            self.stream = sd.OutputStream(samplerate=self.fs, channels=self.data.shape[1], callback=self._callback)
            self.stream.start()

        self.play_thread = threading.Thread(target=self._wait_for_completion)
        self.play_thread.start()

    def _wait_for_completion(self):
        """ Keep thread alive until playback completes """
        while self.is_playing and self.current_position < len(self.data):
            # print(f"Playing: {self.current_position}/{len(self.data)} samples ({self.current_position / self.fs:.2f} sec)", end="")
            if self._playing_callback:
                self._playing_callback(self)
            if self._position_callback:
                self._position_callback(self)
            time.sleep(1)
        if self.current_position >= len(self.data):
            self.is_playing = False  # Auto-pause instead of stopping
            if self._done_callback:
                self._done_callback(self)
        if self.is_stopped:
            self._reset()  # Only reset if manually stopped

    def pause(self):
        """ Pause playback (but keep position) """
        with self.lock:
            self.is_playing = False

    def stop(self):
        """ Stop playback and reset position """
        with self.lock:
            self.is_playing = False
            self.is_streaming = False # stop streaming
            self.is_stopped = True  # Indicate manual stop
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self._reset()

    def _reset(self):
        """ Reset position after stop """
        with self.lock:
            self.current_position = 0
        if self._position_callback:
            self._position_callback(self)

    def jump_to(self, seconds):
        """ Jump to a specific time (in seconds) in the track """
        with self.lock:
            # Round to ensure exact sample position
            new_position = round(seconds * self.fs)

            # Stay within valid range
            new_position = max(0, min(new_position, len(self.data)))

            print(f"Jumping to: {seconds:.2f} sec, {new_position}/{len(self.data)} samples")

        self.current_position = new_position  # Set new position

        if self.is_playing:
            self.pause()  # Pause before seeking
            time.sleep(0.1)  # Ensure buffer clears
            self.play()  # Resume playback

        else:
            if self.is_done and self._done_callback:
                self._done_callback(self)

        if self._position_callback:
            self._position_callback(self)


    def append_data(self, data):
        """ Append new data to the end of the track """
        if data.ndim == 1:
            data = data[:, np.newaxis]
        self.data = np.concatenate([self.data, data], axis=0)
        if self._callback_on_data_arrived:
            self._callback_on_data_arrived(self)

    def append_file(self, filename):
        """ Append new data from a file to the end of the track """
        data, fs = read_audio(filename)
        if fs != self.fs:
            raise ValueError("Sample rate of file does not match current track")
        self.append_data(data)
        self.filepaths.append(str(filename))
        if self._callback_on_file_arrived:
            self._callback_on_file_arrived(self)

    @classmethod
    def from_files(cls, filenames, callback=None, callback_loop=None):

        # Create an iterator from the filenames list
        logger.info(f"Loading files: {filenames}")
        filenames_iter = iter(filenames)

        # Get the first filename and create an AudioPlayer instance
        first_filename = next(filenames_iter)
        player = cls.from_file(first_filename)
        if callback_loop:
            player.on_file_arrived(callback_loop)

        # Start a thread to append the remaining files
        def append_remaining_files():
            player.is_streaming = True
            try:
                for filename in filenames_iter:
                    player.append_file(filename)
                    if not player.is_streaming:
                        logger.info("Streaming interrupted manually.")
                        break
            except Exception as e:
                logger.warning(f"Error appending files: {e}")
            finally:
                logger.info("Done downloading files.")
                player.is_streaming = False
                if callback:
                    callback(player)

        player.is_streaming = True
        player._append_thread = threading.Thread(target=append_remaining_files)
        player._append_thread.start()

        # Return the first instance immediately
        return player

    def wait(self):
        """ Wait for playback to finish """
        logger.debug("player wait called")
        if self.play_thread:
            logger.debug("player waiting for play thread")
            self.play_thread.join()
        if self.is_streaming:
            logger.debug("player waiting for append/streaming thread")
            self._append_thread.join()

    @property
    def total_duration(self):
        """ Duration of the record in seconds """
        return len(self.data) / self.fs

    @property
    def current_position_seconds(self):
        """ Current position in seconds """
        return self.current_position / self.fs

    def __del__(self):
        logger.info("player deleted")
        self.stop()


    def open_external(player, external_player=None, terminal=False, termux=False):

        current_position = player.current_position_seconds

        if player.is_playing:
            player.pause() # pause so streaming continue

        playlist = "\n".join(player.filepaths)
        playlist_file = get_cache_path("playlist.m3u")
        with open(playlist_file, "w") as f:
            f.write(playlist)

        # # callback for the case streaming is going on
        # def append_file_to_playlist(player):
        #     file = player.filepaths[-1]
        #     with open(playlist_file, "a") as f:
        #         f.write("\n"+file)

        # player.on_file_arrived(append_file_to_playlist)

        if external_player is None:
            candidates = ["termux-open" if termux else "xdg-open"]
            if terminal or termux:
                candidates.insert(0, "mpv")

        else:
            candidates = [external_player]

        for candidate in candidates:
            try:
                logger.info(f"Try opening playlist with: {candidate}")
                cmd = [candidate, playlist_file]
                if candidate.split(os.path.sep)[-1] == "mpv":
                    cmd.append(f"--start={current_position}")
                logger.info(cmd)
                sp.check_call(cmd)
                return
            except sp.CalledProcessError:
                continue

        raise ValueError("Failed to open playlist with an external player")
