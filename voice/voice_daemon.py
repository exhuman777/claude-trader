#!/usr/bin/env python3
"""
Voice Daemon - Records voice and saves transcript to file
Claude Code reads the file and executes commands
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.recorder import record_push_to_talk
from voice.transcribe import transcribe

TRANSCRIPT_FILE = Path(__file__).parent / "latest_command.txt"
HISTORY_FILE = Path(__file__).parent / "command_history.txt"


def save_transcript(text: str):
    """Save transcript for Claude to read"""
    TRANSCRIPT_FILE.write_text(text)

    # Also append to history
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} | {text}\n")

    print(f"✓ Saved: {text[:60]}...")


def main():
    print("=" * 50)
    print("  Voice Daemon for Claude Trading")
    print("=" * 50)
    print("SPACE = record → transcribe → save")
    print("Claude will read and execute automatically")
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
                save_transcript(text)
                print(f'\n"{text}"\n')
                print("→ Claude can now read this command")
            else:
                print("(No speech detected)")

            print()

        except KeyboardInterrupt:
            print("\nBye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
