#!/usr/bin/env python3
"""
Whisper transcription for Polish and English
Uses whisper.cpp or OpenAI whisper as fallback
"""
import subprocess
import os
from pathlib import Path

# Paths - adjust for your setup
WHISPER_CPP = Path.home() / ".claude1/whisper.cpp"
WHISPER_MODEL_PL = "jonatasgrosman/whisper-medium-pl-v2"
WHISPER_MODEL_EN = "base.en"

# Prefer whisper.cpp if built, else Python
USE_CPP = (WHISPER_CPP / "build/bin/whisper-cli").exists()


def transcribe_cpp(audio_path: Path, language: str = "auto") -> str:
    """Transcribe using whisper.cpp CLI"""
    model_path = WHISPER_CPP / "models/ggml-base.bin"

    cmd = [
        str(WHISPER_CPP / "build/bin/whisper-cli"),
        "-m", str(model_path),
        "-f", str(audio_path),
        "--no-timestamps",
        "-l", language if language != "auto" else "auto",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"whisper.cpp failed: {result.stderr}")

    return result.stdout.strip()


def transcribe_python(audio_path: Path, language: str = "auto") -> str:
    """Transcribe using Python whisper library"""
    try:
        import whisper
    except ImportError:
        raise ImportError("pip install openai-whisper")

    model = whisper.load_model("base")
    result = model.transcribe(
        str(audio_path),
        language=None if language == "auto" else language,
    )
    return result["text"].strip()


def transcribe_polish(audio_path: Path) -> str:
    """Transcribe using Polish-optimized model via transformers"""
    try:
        from transformers import pipeline
    except ImportError:
        raise ImportError("pip install transformers torch")

    pipe = pipeline(
        "automatic-speech-recognition",
        model=WHISPER_MODEL_PL,
        chunk_length_s=30,
    )

    result = pipe(str(audio_path))
    return result["text"].strip()


def transcribe(audio_path: Path, language: str = "auto") -> str:
    """
    Transcribe audio file to text.

    Args:
        audio_path: Path to WAV file
        language: "pl" for Polish, "en" for English, "auto" for detection

    Returns:
        Transcribed text
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Polish-specific model
    if language == "pl":
        try:
            return transcribe_polish(audio_path)
        except ImportError:
            print("Polish model unavailable, falling back to base whisper")

    # Use whisper.cpp if available
    if USE_CPP:
        return transcribe_cpp(audio_path, language)

    # Fallback to Python whisper
    return transcribe_python(audio_path, language)


def detect_language(text: str) -> str:
    """Simple language detection based on common Polish characters"""
    polish_chars = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
    polish_words = {"kup", "sprzedaj", "zamówień", "pokaż", "anuluj", "akcji", "po"}

    text_lower = text.lower()

    # Check for Polish-specific characters
    if any(c in text for c in polish_chars):
        return "pl"

    # Check for common Polish words
    if any(word in text_lower for word in polish_words):
        return "pl"

    return "en"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio.wav> [language]")
        sys.exit(1)

    audio = Path(sys.argv[1])
    lang = sys.argv[2] if len(sys.argv) > 2 else "auto"

    text = transcribe(audio, lang)
    print(f"Transcription: {text}")
    print(f"Detected language: {detect_language(text)}")
