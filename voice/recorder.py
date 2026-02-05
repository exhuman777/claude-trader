#!/usr/bin/env python3
"""
Push-to-talk voice recorder
Hold Enter to record, release to stop
"""
import sounddevice as sd
import numpy as np
import wave
import sys
import termios
import tty
from pathlib import Path

SAMPLE_RATE = 16000  # whisper.cpp native rate
CHANNELS = 1
OUTPUT_PATH = Path(__file__).parent / "recording.wav"


def record_until_enter() -> Path:
    """Record until user presses ENTER. Returns path to WAV file."""
    print("🎤 Recording... press ENTER when done")

    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16',
        callback=callback
    )

    with stream:
        input()  # Wait for ENTER

    print("✓ Recording stopped")

    if not frames:
        return None

    # Save WAV
    audio = np.concatenate(frames, axis=0)
    with wave.open(str(OUTPUT_PATH), 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    duration = len(audio) / SAMPLE_RATE
    print(f"Saved {duration:.1f}s to {OUTPUT_PATH.name}")
    return OUTPUT_PATH


def record_push_to_talk() -> Path:
    """Record while SPACE is held. Returns path to WAV file."""
    print("Hold SPACE to record (release to stop)... [q to quit]")

    # Wait for Space press
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        # Wait for keypress
        ch = sys.stdin.read(1)
        if ch == 'q':
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return None
        if ch != ' ':
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            print(f"\r(Press SPACE to record, q to quit)")
            return None

        print("\r Recording... ", end="", flush=True)

        frames = []

        def callback(indata, frame_count, time_info, status):
            frames.append(indata.copy())

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='int16',
            callback=callback
        )

        with stream:
            # Wait for key release
            sys.stdin.read(1)

        print("\r Done!          ")

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    if not frames:
        return None

    # Save WAV
    audio = np.concatenate(frames, axis=0)
    with wave.open(str(OUTPUT_PATH), 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    duration = len(audio) / SAMPLE_RATE
    print(f"Saved {duration:.1f}s to {OUTPUT_PATH.name}")
    return OUTPUT_PATH


def record_duration(seconds: float) -> Path:
    """Record for fixed duration. Returns path to WAV file."""
    print(f"Recording for {seconds}s...")

    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16'
    )
    sd.wait()

    with wave.open(str(OUTPUT_PATH), 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    print(f"Saved to {OUTPUT_PATH.name}")
    return OUTPUT_PATH


if __name__ == "__main__":
    path = record_push_to_talk()
    if path:
        print(f"Audio saved: {path}")
