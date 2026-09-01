import io
import os
from typing import Optional
import speech_recognition as sr
from ai.llm import client
from core.config_manager import config
from core.ui import console

def transcribe_audio(audio_data: sr.AudioData) -> Optional[str]:
    """
    Whisper transcription using Groq API with optimized in-memory streaming
    """
    if audio_data is None:
        return None

    try:
        # Convert audio data to in-memory WAV file
        wav_data = audio_data.get_wav_data()
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "speech.wav"  # Groq requires a filename with an extension

        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=config.TRANSCRIPTION_MODEL,
            response_format="text",
            language="en",
            prompt=(
                f"Jarvis, Sir, {getattr(config, 'WAKE_WORDS', ['Sir'])[0]}, "
                "systems online, schedule."
            )
        )
        if not transcription:
            return None

        result_text = str(transcription).strip()

        # Clean common Whisper hallucination outputs
        cleaned = result_text.lower().replace(".", "").replace(",", "").strip()
        for noise in getattr(config, 'NOISE_WORDS', []):
            if cleaned == noise.lower().replace(".", "").replace(",", "").strip():
                return None

        return result_text
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Transcription Error:[/] {e}")
        return None

