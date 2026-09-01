import asyncio
import io
import edge_tts
import pygame
from core.config_manager import config
from core.ui import console


async def generate_tts_audio(text: str) -> bytearray | None:
    """
    Generate TTS audio bytes in memory WITHOUT playing.
    Returns a bytearray of MP3 audio data, or None if nothing to speak.
    Separating generation from playback enables the pipeline:
      sentence 1 plays -> sentence 2 generates concurrently -> no gap.
    """
    try:
        from core.text_utils import strip_action_tags, strip_emotion_tag

        clean_text = strip_action_tags(text)
        clean_text, pitch, rate = strip_emotion_tag(clean_text)

        if "[IGNORE]" in clean_text or "[SKIP]" in clean_text or not clean_text.strip():
            return None

        communicate = edge_tts.Communicate(clean_text, config.JARVIS_VOICE, pitch=pitch, rate=rate)

        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        return audio_data if audio_data else None
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]TTS Generation Error:[/] {e}")
        return None


def stop_tts() -> None:
    """
    Instantly stop all active Pygame audio playback and clear speaking state flags.
    Used for instant user interruption.
    """
    try:
        pygame.mixer.stop()
    except Exception:
        pass
    config.is_speaking = False
    import time
    config.last_speak_time = time.time()


async def play_tts_audio(audio_data: bytearray) -> None:
    """
    Play pre-generated TTS audio bytes directly from memory via pygame.
    Manages music ducking and supports instant user interruption.
    """
    if not audio_data:
        return

    music_was_playing = pygame.mixer.music.get_busy()
    if music_was_playing:
        pygame.mixer.music.set_volume(0.15)

    config.is_speaking = True
    try:
        sound = pygame.mixer.Sound(io.BytesIO(audio_data))
        channel = sound.play()

        if channel is None:
            channel = pygame.mixer.find_channel(force=True)
            if channel:
                channel.play(sound)

        if channel:
            while channel.get_busy():
                # If config.is_speaking flag was cleared externally (user interrupted), stop playback immediately
                if not getattr(config, 'is_speaking', True):
                    channel.stop()
                    pygame.mixer.stop()
                    break
                await asyncio.sleep(0.03)
    finally:
        config.is_speaking = False
        import time
        config.last_speak_time = time.time()
        if music_was_playing:
            pygame.mixer.music.set_volume(1.0)


async def speak_jarvis(text: str) -> None:
    """
    Jarvis voice output: generate TTS audio then play it.
    Used for one-shot utterances (greetings, skill results, errors).
    For streaming responses, use generate_tts_audio + play_tts_audio directly.
    """
    try:
        audio_data = await generate_tts_audio(text)
        if audio_data:
            await play_tts_audio(audio_data)
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Audio Error:[/] {e}")
    finally:
        config.is_speaking = False
        import time
        config.last_speak_time = time.time()
