# SPDX-FileCopyrightText: 2026 ReggaeTalkerCircuitPython contributors
#
# SPDX-License-Identifier: MIT
"""QT Py ESP32-S3 + Adafruit Audio BFF SD-card WAV jukebox.

On startup this script mounts the Audio BFF microSD card, builds a sorted
playlist of WAV files found on the card, and waits for the QT Py BOOT button.
Every press stops any current playback and starts the next WAV in the playlist,
wrapping back to the first file after the last file.
"""

import os
import time

import adafruit_sdcard
import audiobusio
import audiocore
import audiomixer
import board
import digitalio
import storage

SD_MOUNT = "/sd"
WAV_EXTENSION = ".wav"
DEBOUNCE_SECONDS = 0.05
DIRECTORY_FLAG = 0x4000
# CircuitPython audiocore.WaveFile accepts an optional writable buffer from
# 8-1024 bytes. Use the maximum size so playback does not need to allocate
# internal buffers each time a WAV starts.
WAVE_BUFFER_SIZE = 1024

# Adafruit Audio BFF default pinout for QT Py S2/S3/RP2040:
# A0 = SD card chip select, A1 = I2S data, A2 = I2S word select/LRCLK,
# A3 = I2S bit clock/BCLK. The SD card uses the QT Py's default SPI pins.
SD_CHIP_SELECT = board.A0
I2S_DATA = board.A1
I2S_WORD_SELECT = board.A2
I2S_BIT_CLOCK = board.A3


card_cs = digitalio.DigitalInOut(SD_CHIP_SELECT)
# Match Adafruit's Audio BFF examples: leave chip-select pulled high until the
# SDCard driver takes ownership of the pin.
card_cs.switch_to_input(pull=digitalio.Pull.UP)

boot_button = digitalio.DigitalInOut(board.BUTTON)
boot_button.switch_to_input(pull=digitalio.Pull.UP)

audio = audiobusio.I2SOut(I2S_BIT_CLOCK, I2S_WORD_SELECT, I2S_DATA)
current_file = None
mixer = None
wave_buffer = bytearray(WAVE_BUFFER_SIZE)


def is_directory(path):
    """Return True when path points to a directory."""
    return bool(os.stat(path)[0] & DIRECTORY_FLAG)


def ensure_sd_mount_point():
    """Make sure CircuitPython has a directory available for the SD mount."""
    try:
        if is_directory(SD_MOUNT):
            return
    except OSError:
        pass

    try:
        os.mkdir(SD_MOUNT)
    except OSError as error:
        print("Create a folder named sd on CIRCUITPY, then reset the board.")
        raise error


def mount_sd_card():
    """Mount the Audio BFF SD card and return its filesystem path."""
    ensure_sd_mount_point()
    sdcard = adafruit_sdcard.SDCard(board.SPI(), card_cs)
    storage.mount(storage.VfsFat(sdcard), SD_MOUNT)
    print("Mounted SD card at", SD_MOUNT)
    return SD_MOUNT


def append_wav_files(directory, playlist):
    """Append WAV files from directory and its subdirectories to playlist."""
    for filename in os.listdir(directory):
        if filename.startswith("."):
            continue

        path = directory + "/" + filename
        try:
            directory_entry = is_directory(path)
        except OSError:
            continue

        if directory_entry:
            append_wav_files(path, playlist)
        elif filename.lower().endswith(WAV_EXTENSION):
            playlist.append(path)


def wav_files_on_sd():
    """Return a sorted playlist of WAV files on the SD card."""
    files = []
    append_wav_files(SD_MOUNT, files)
    files.sort(key=lambda path: path.lower())
    return files


def stop_audio():
    """Stop playback and close the active WAV file, if any."""
    global current_file
    if mixer and mixer.voice[0].playing:
        mixer.voice[0].stop()
    if audio.playing:
        audio.stop()
    if current_file:
        current_file.close()
        current_file = None


def play_wav(path):
    """Play a WAV file through the Audio BFF at full software volume."""
    global current_file, mixer
    stop_audio()
    print("Playing", path)
    current_file = open(path, "rb")
    wave = audiocore.WaveFile(current_file, wave_buffer)
    mixer = audiomixer.Mixer(
        voice_count=1,
        sample_rate=wave.sample_rate,
        channel_count=wave.channel_count,
        bits_per_sample=wave.bits_per_sample,
        samples_signed=True,
    )
    mixer.voice[0].level = 1.0
    audio.play(mixer)
    mixer.voice[0].play(wave)


def wait_for_button_press():
    """Block until the active-low BOOT button is pressed and debounced."""
    while boot_button.value:
        time.sleep(0.01)
    time.sleep(DEBOUNCE_SECONDS)
    if boot_button.value:
        return False
    while not boot_button.value:
        time.sleep(0.01)
    time.sleep(DEBOUNCE_SECONDS)
    return True


mount_sd_card()
wav_files = wav_files_on_sd()
print("Found", len(wav_files), "WAV file(s):", wav_files)

if not wav_files:
    print("No WAV files found on the SD card. Add .wav files and reset the board.")
else:
    next_wav = 0
    while True:
        if wait_for_button_press():
            play_wav(wav_files[next_wav])
            next_wav = (next_wav + 1) % len(wav_files)
