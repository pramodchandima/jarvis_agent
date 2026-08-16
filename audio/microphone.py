from typing import Optional
import speech_recognition as sr
from core.config_manager import config
from core.ui import console

def listen_realtime() -> Optional[sr.AudioData]:
    """
    VAD-based listening with optimized microphone settings
    Returns audio data or None if no input detected
    """
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = config.DYNAMIC_ENERGY
    recognizer.energy_threshold = config.ENERGY_THRESHOLD
    recognizer.pause_threshold = getattr(config, 'PAUSE_THRESHOLD', 0.8)
    recognizer.phrase_threshold = getattr(config, 'PHRASE_THRESHOLD', 0.3)

    with sr.Microphone() as source:
        console.print("\n[bold blue]Listening...[/] (At your service, sir)")
        try:
            recognizer.adjust_for_ambient_noise(source, duration=config.ADJUST_DURATION)
            audio = recognizer.listen(source, timeout=None, phrase_time_limit=None)
            return audio
        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[red]Microphone Error:[/] {e}")
            return None
