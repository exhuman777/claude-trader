#!/usr/bin/env python3
"""
Simple voice recorder - saves transcript to file
Claude Code reads and executes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.recorder import record_until_enter
from voice.transcribe import transcribe

TRANSCRIPT_FILE = Path(__file__).parent / "transcript.txt"


def main():
    print("=" * 50)
    print("  Voice Recorder for Claude Trading")
    print("=" * 50)
    print("ENTER = start, ENTER = stop, q = quit")
    print("Transcript saved → tell Claude 'voice' to execute")
    print()

    while True:
        cmd = input("[ENTER to record, q to quit]: ").strip()
        if cmd.lower() == 'q':
            print("Bye!")
            break

        audio = record_until_enter()
        if audio is None:
            continue

        print("Transcribing...")
        text = transcribe(audio, "auto")

        if text and len(text) > 2:
            TRANSCRIPT_FILE.write_text(text)
            print(f'\n✓ "{text}"')
            print(f"→ Saved to {TRANSCRIPT_FILE.name}")
            print("→ Tell Claude: 'voice' or 'check voice'")
        else:
            print("(No speech detected)")

        print()


if __name__ == "__main__":
    main()
