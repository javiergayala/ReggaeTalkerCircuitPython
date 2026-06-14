# ReggaeTalkerCircuitPython

CircuitPython script for a QT Py ESP32-S3 with an Adafruit Audio BFF and a microSD card.

## What it does

On boot, `code.py`:

1. Mounts the Audio BFF microSD card at `/sd`.
2. Reads `.wav` files from the SD card into a sorted playlist, including files in subdirectories.
3. Configures the QT Py ESP32-S3 BOOT button as an input with a pull-up.
4. Plays the next WAV file each time BOOT is pressed.
5. Wraps back to the first WAV file after the last one.
6. Uses a pre-allocated 1024-byte writable buffer for `audiocore.WaveFile` playback and sets the software mixer voice level to `1.0` for maximum software volume. For more physical output, adjust the Audio BFF gain jumper and use an appropriately rated 4-8Ω speaker.

## WAV playback buffer

`code.py` creates one reusable `bytearray(1024)` buffer for `audiocore.WaveFile`. CircuitPython allows WaveFile buffers from 8 to 1024 bytes; this script uses the maximum supported size to avoid repeated internal audio-buffer allocation when changing tracks.

## Hardware pinout

The script uses the Audio BFF default QT Py pinout:

| Signal | QT Py pin |
| --- | --- |
| SD card chip select | `A0` |
| I2S audio data | `A1` |
| I2S word select / LRCLK | `A2` |
| I2S bit clock / BCLK | `A3` |
| Button | `BUTTON` / BOOT |

## CircuitPython setup

Copy `code.py` to the root of the QT Py ESP32-S3 `CIRCUITPY` drive.

Install the required libraries in `CIRCUITPY/lib`:

- `adafruit_sdcard.mpy`
- `adafruit_bus_device/`

Create a folder named `sd` on the `CIRCUITPY` drive if it is not already present. Put your `.wav` files anywhere on the microSD card, insert the card into the Audio BFF, and reset the QT Py.
