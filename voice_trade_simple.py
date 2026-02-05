#!/usr/bin/env python3
"""
Voice Trading - One Terminal Flow
Voice → Transcribe → Claude CLI → Trade
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from voice.recorder import record_until_enter
from voice.transcribe import transcribe


def run_claude(prompt: str):
    """Run claude CLI with prompt"""
    print("\n" + "=" * 50)
    print("Claude is thinking...")
    print("=" * 50 + "\n")

    # Use claude CLI which has auth + all tools
    subprocess.run(
        ['claude', '-p', prompt, '--no-input'],
        cwd=str(Path(__file__).parent)
    )


def main():
    print("=" * 60)
    print("  Voice Trading - One Terminal")
    print("=" * 60)
    print("ENTER = record | ENTER = stop | type = text | q = quit")
    print()

    while True:
        try:
            cmd = input("\n> ").strip()

            if cmd.lower() in ['q', 'quit', 'exit']:
                print("Bye!")
                break

            if cmd == '':
                # Voice mode
                audio = record_until_enter()
                if audio is None:
                    continue

                print("Transcribing...")
                text = transcribe(audio, "auto")

                if not text or len(text) < 3:
                    print("(No speech detected)")
                    continue

                print(f'\n🎤 "{text}"')

                confirm = input("Send to Claude? [Y/n]: ").strip().lower()
                if confirm == 'n':
                    continue

                run_claude(text)

            else:
                # Text mode
                run_claude(cmd)

        except KeyboardInterrupt:
            print("\n(Ctrl+C) Type 'q' to quit")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
