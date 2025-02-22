"""Based on a conversation with Chat GPT...
"""
import sounddevice as sd
import soundfile as sf
import threading
import numpy as np
import time
from bard.util import logger

class AudioPlayer:
    def __init__(self, data, fs):
        if data.ndim == 1:
            data = data[:, np.newaxis]
        self.data, self.fs = data, fs
        self.stream = None
        self.play_thread = None
        self.current_position = 0  # Track position in samples
        self.is_playing = False
        self.is_stopped = False  # Track if we should reset position
        self.is_streaming = False
        self.lock = threading.Lock()
        self._done_callback = None

    @classmethod
    def from_file(cls, filename):
        print("Loading file:", filename)
        data, fs = sf.read(filename, dtype='float32')  # Load file into memory
        return cls(data, fs)

    def on_done(self, callback):
        self._done_callback = callback
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
            print(f"Playing: {self.current_position}/{len(self.data)} samples ({self.current_position / self.fs:.2f} sec)")
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

    def append_data(self, data):
        """ Append new data to the end of the track """
        if data.ndim == 1:
            data = data[:, np.newaxis]
        self.data = np.concatenate([self.data, data], axis=0)

    def append_file(self, filename):
        """ Append new data from a file to the end of the track """
        data, fs = sf.read(filename, dtype='float32')
        if fs != self.fs:
            raise ValueError("Sample rate of file does not match current track")
        self.append_data(data)

    @classmethod
    def from_files(cls, filenames, callback=None, callback_loop=None):
        # Create an iterator from the filenames list
        print("Loading files:", filenames)
        filenames_iter = iter(filenames)

        # Get the first filename and create an AudioPlayer instance
        first_filename = next(filenames_iter)
        player = cls.from_file(first_filename)

        # Start a thread to append the remaining files
        def append_remaining_files():
            try:
                for filename in filenames_iter:
                    player.is_streaming = True
                    player.append_file(filename)
                    if callback_loop:
                        callback_loop(player)
            except Exception as e:
                print(f"Error appending files: {e}")
            finally:
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