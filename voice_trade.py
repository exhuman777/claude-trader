#!/usr/bin/env python3
"""
Voice Trading with Claude Code
Records voice → Transcribes → Sends to Claude CLI
All existing features (whale spotting, research, memory) work via Claude
"""
import sys
import subprocess
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from voice.recorder import record_push_to_talk
from voice.transcribe import transcribe


def run_claude_with_prompt(prompt: str):
    """Run claude CLI with the given prompt"""
    print(f"\n→ Sending to Claude: {prompt[:80]}...")
    print("-" * 50)

    # Run claude in non-interactive mode with the prompt
    result = subprocess.run(
        ['claude', '-p', prompt],
        cwd=str(Path(__file__).parent),
        capture_output=False
    )
    return result.returncode


def main():
    print("=" * 50)
    print("  Voice Trading with Claude")
    print("=" * 50)
    print("Speak naturally - Claude does the rest")
    print("SPACE = record, q = quit")
    print()
    print("Examples:")
    print('  "Show me whale trades over $5000"')
    print('  "Find Trump markets and show orderbook"')
    print('  "Buy $10 of the top volume market"')
    print()

    while True:
        try:
            audio = record_push_to_talk()
            if audio is None:
                print("Bye!")
                break

            print("Transcribing...")
            text = transcribe(audio, "auto")

            if not text or len(text) < 3:
                print("(No speech detected)")
                continue

            print(f'\nYou said: "{text}"')
            confirm = input("Send to Claude? [Y/n]: ").strip().lower()

            if confirm != 'n':
                run_claude_with_prompt(text)

            print()

        except KeyboardInterrupt:
            print("\nBye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
