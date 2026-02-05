#!/usr/bin/env python3
"""
Voice Trading Pipeline
Record → Transcribe → Parse → Execute

Supports Polish and English voice commands.
Uses memory system to learn across sessions.
"""
import sys
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from recorder import record_push_to_talk, record_duration
from transcribe import transcribe, detect_language

# Import command parser from interactive.py
from interactive import process_command, current_event, current_markets

# Memory system
from memory import get_memory, get_mindmap

# Polish → English command mapping
POLISH_COMMANDS = {
    # Actions
    "kup": "buy",
    "kupić": "buy",
    "sprzedaj": "sell",
    "sprzedać": "sell",
    "anuluj": "cancel",
    "pokaż": "show",
    "sprawdź": "check",

    # Nouns
    "zamówienia": "orders",
    "zamówień": "orders",
    "pozycje": "positions",
    "cena": "price",
    "cenę": "price",
    "wszystko": "all",
    "wszystkie": "all",

    # Numbers
    "jeden": "1", "dwa": "2", "trzy": "3", "cztery": "4",
    "pięć": "5", "sześć": "6", "siedem": "7", "osiem": "8",
    "dziewięć": "9", "dziesięć": "10", "dwadzieścia": "20",
    "trzydzieści": "30", "czterdzieści": "40", "pięćdziesiąt": "50",

    # Units
    "akcji": "shares",
    "akcje": "shares",
    "centów": "cents",
    "centy": "cents",
    "po": "at",

    # Months
    "stycznia": "jan", "lutego": "feb", "marca": "mar",
    "kwietnia": "apr", "maja": "may", "czerwca": "jun",
    "lipca": "jul", "sierpnia": "aug", "września": "sep",
    "października": "oct", "listopada": "nov", "grudnia": "dec",
}


def translate_polish(text: str) -> str:
    """Translate Polish voice command to English equivalent"""
    words = text.lower().split()
    translated = []

    for word in words:
        translated.append(POLISH_COMMANDS.get(word, word))

    return " ".join(translated)


def voice_to_command(text: str) -> str:
    """Convert voice transcript to trading command"""
    lang = detect_language(text)

    if lang == "pl":
        print(f"  [PL] {text}")
        text = translate_polish(text)
        print(f"  [EN] {text}")

    return text


def voice_loop():
    """Main voice trading loop"""
    memory = get_memory()
    mindmap = get_mindmap()

    print("=" * 60)
    print("  Voice Trading - Polymarket")
    print("=" * 60)
    print("Commands: Polish or English")
    print("Hold SPACE to speak, 'q' to quit")

    # Show session context from memory
    context = memory.get_session_context()
    if context and len(context) > 50:
        print("\n[Memory loaded - using past insights]")

    best = memory.get_best_practices()
    if best:
        print(f"Best practices: {', '.join(best[:3])}")

    print()

    while True:
        try:
            # Record audio
            audio_path = record_push_to_talk()

            if audio_path is None:
                # User pressed q or wrong key - check if quit
                memory.save_all()
                mindmap.save()
                print("Memory saved. Bye!")
                break

            # Transcribe
            print("Transcribing...")
            text = transcribe(audio_path, language="auto")
            print(f"\nYou said: \"{text}\"")

            if not text or len(text) < 2:
                print("(No speech detected)")
                continue

            # Check memory for similar past queries
            similar = memory.find_similar_query(text)
            if similar:
                print(f"[Previous result: {similar['result'][:80]}...]")

            # Convert to command
            command = voice_to_command(text)

            # Show preview
            print(f"\nCommand: {command}")
            confirm = input("Execute? [y/N/edit]: ").strip().lower()

            if confirm == 'y':
                process_command(command)
                # Record in memory
                memory.record_query(text, f"Executed: {command}")
                if 'buy' in command or 'sell' in command:
                    memory.record_trade({"command": command, "voice": text})
            elif confirm.startswith('e'):
                # Let user edit the command
                edited = input(f"Edit [{command}]: ").strip()
                if edited:
                    process_command(edited)
                    memory.record_query(text, f"Edited to: {edited}")
                else:
                    process_command(command)
            else:
                print("Cancelled")

            print()

        except KeyboardInterrupt:
            print("\n(Ctrl+C) Use 'q' to quit")
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Voice trading for Polymarket")
    parser.add_argument("--lang", choices=["auto", "pl", "en"], default="auto",
                        help="Force language (default: auto-detect)")
    parser.add_argument("--test", type=str, help="Test with audio file instead of mic")

    args = parser.parse_args()

    if args.test:
        # Test mode - process a single audio file
        text = transcribe(Path(args.test), args.lang)
        print(f"Transcript: {text}")
        command = voice_to_command(text)
        print(f"Command: {command}")
        return

    # Interactive voice loop
    voice_loop()


if __name__ == "__main__":
    main()
