#!/usr/bin/env python3
"""
Voice Input for Claude Code
Records speech → Transcribes → Copies to clipboard
Then paste into Claude Code session
"""
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.recorder import record_push_to_talk
from voice.transcribe import transcribe


def copy_to_clipboard(text: str):
    """Copy text to macOS clipboard"""
    subprocess.run(['pbcopy'], input=text.encode(), check=True)


def voice_input_loop():
    """Record voice, transcribe, copy to clipboard"""
    print("=" * 50)
    print("  Voice Input for Claude Trading")
    print("=" * 50)
    print("SPACE = record, then paste into Claude")
    print("q = quit")
    print()

    while True:
        try:
            audio = record_push_to_talk()
            if audio is None:
                print("Bye!")
                break

            print("Transcribing...")
            text = transcribe(audio, "auto")

            if text and len(text) > 2:
                print(f'\n"{text}"')
                copy_to_clipboard(text)
                print("→ Copied to clipboard! Paste into Claude (Cmd+V)")
            else:
                print("(No speech detected)")

            print()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    voice_input_loop()
