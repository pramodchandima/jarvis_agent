import os
import tempfile
from typing import Optional
import speech_recognition as sr
from ai.llm import client
from core.config_manager import config
from core.ui import console

def transcribe_audio(audio_data: sr.AudioData) -> Optional[str]:
    """
    Whisper transcription using Groq API with optimized streaming
    """
    if audio_data is None:
        return None

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        with open(tmp_path, "wb") as f:
            f.write(audio_data.get_wav_data())

        with open(tmp_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(tmp_path), file.read()),
                model=config.TRANSCRIPTION_MODEL,
                response_format="text",
                language="en",
                prompt=(
                    f"Jarvis, Sir, {getattr(config, 'WAKE_WORDS', ['Sir'])[0]}, "
                    "systems online, schedule."
                )
            )
        return transcription
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Transcription Error:[/] {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
