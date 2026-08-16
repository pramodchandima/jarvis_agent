import asyncio
import os
import re
import tempfile
import edge_tts
import pygame
from core.config_manager import config
from core.ui import console

async def speak_jarvis(text: str) -> None:
    """
    Jarvis voice output with optimized performance using pygame Sound channel
    """
    try:
        from core.text_utils import strip_action_tags, strip_emotion_tag
        
        # Strip internal tags and apply corresponding pitch/rate adjustments
        clean_text = strip_action_tags(text)
        clean_text, pitch, rate = strip_emotion_tag(clean_text)

        if "[IGNORE]" in clean_text or "[SKIP]" in clean_text or not clean_text.strip():
            return

        # TTS conversion
        communicate = edge_tts.Communicate(clean_text, config.JARVIS_VOICE, pitch=pitch, rate=rate)

        # Use temp file for audio
        fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        try:
            await communicate.save(tmp_path)

            # Duck music if it is currently playing
            music_was_playing = pygame.mixer.music.get_busy()
            if music_was_playing:
                pygame.mixer.music.set_volume(0.15)

            # Set speaking state flag
            config.is_speaking = True

            # Load and play audio as Sound (non-blocking to background music channel)
            sound = pygame.mixer.Sound(tmp_path)
            channel = sound.play()
            
            if channel is None:
                # Force play by seizing any available channel
                channel = pygame.mixer.find_channel(force=True)
                if channel:
                    channel.play(sound)

            # Wait for playback with minimal overhead
            if channel:
                while channel.get_busy():
                    await asyncio.sleep(0.05)

            # Reset speaking state and store timestamp
            config.is_speaking = False
            import time
            config.last_speak_time = time.time()

            # Restore music volume if ducked
            if music_was_playing:
                pygame.mixer.music.set_volume(1.0)
        finally:
            # Reset speaking state on exception/finally as safety
            config.is_speaking = False
            import time
            config.last_speak_time = time.time()
            # Ensure cleanup
            await asyncio.sleep(0.05)
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Audio Error:[/] {e}")
