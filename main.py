"""
JARVIS AI Assistant - Optimized Main Application Script
High-Performance Version with Intelligent Interactive Decision Making
Handles voice recognition, AI logic, and system interactions efficiently.
"""
import asyncio
import sys
import re
import queue
import threading

import pygame
import speech_recognition as sr

from core.config_manager import config
from core.ui import console, show_startup_banner
from core.database import get_recent_conversations, add_memory
from audio.tts import speak_jarvis
from audio.stt import transcribe_audio
from audio.music_player import stop_music
from ai.intent_analyzer import analyze_request_complexity
from ai.llm import get_jarvis_response, messages, client
from tools.reminder_scheduler import start_reminder_scheduler

# Initialize Pygame Mixer at the root
pygame.mixer.init()
pygame.mixer.set_num_channels(32)

# Shared input queue to handle concurrent voice & text inputs
input_queue = queue.Queue()

# Flag to block processing voice while Jarvis is talking
jarvis_is_speaking = False

def console_input_thread():
    """Thread to read console inputs concurrently without blocking speech recognition"""
    while True:
        try:
            text = input().strip()
            if text:
                input_queue.put(("text", text))
        except (KeyboardInterrupt, EOFError):
            input_queue.put(("system", "exit"))
            break

async def run_reflection():
    """Generates a brief summary/reflection of the session and saves it as a memory"""
    console.print("\n[yellow]System: Generating session reflection...[/]")
    try:
        logs = get_recent_conversations(limit=10)
        if not logs:
            return
        log_text = ""
        for role, content in logs:
            clean_content = re.sub(r"\[\[.*?\]\]", "", content, flags=re.DOTALL).strip()
            if clean_content:
                log_text += f"{role}: {clean_content}\n"
        
        if not log_text.strip():
            return
            
        prompt = (
            "Analyze the following J.A.R.V.I.S. conversation logs of this session. "
            "Write a very brief 1-2 sentence summary of what tasks were accomplished, "
            "key topics discussed, or user preferences noted.\n\n"
            f"Logs:\n{log_text}"
        )
        
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256
        )
        summary = completion.choices[0].message.content.strip()
        add_memory("Reflection", summary)
        console.print(f"[bold green]System:[/] Session reflection saved: [italic]{summary}[/]")
    except Exception as e:
        console.print(f"[yellow]Warning:[/] Failed to generate reflection: {e}")

async def dashboard_data_writer_task():
    """Background task to keep dashboard variables updated in data.js and space_data.js"""
    from tools.dashboard_manager import update_dashboard_data
    from tools.space_dashboard_manager import update_space_data
    while True:
        try:
            await asyncio.to_thread(update_dashboard_data)
        except Exception:
            pass
        try:
            await asyncio.to_thread(update_space_data)
        except Exception:
            pass
        try:
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2)

def is_self_echo(user_text: str) -> bool:
    """Check if transcribed voice is an echo of Jarvis's own speech from speakers."""
    import time
    is_speaking = getattr(config, 'is_speaking', False)
    last_speak_time = getattr(config, 'last_speak_time', 0.0)
    time_since_speech = time.time() - last_speak_time

    clean_user = re.sub(r"[^\w\s]", "", user_text.lower()).strip()
    if not clean_user:
        return True

    # 1. ALWAYS check text similarity against recent assistant responses + active speech
    assistant_texts = ["online and ready sir"]
    active_speech = getattr(config, 'current_speaking_text', '')
    if active_speech:
        cleaned_active = re.sub(r"[^\w\s]", "", active_speech.lower()).strip()
        if cleaned_active:
            assistant_texts.append(cleaned_active)

    try:
        from ai.llm import messages
        from core.text_utils import clean_display_text
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                cleaned_ast = re.sub(r"[^\w\s]", "", clean_display_text(msg["content"]).lower()).strip()
                if cleaned_ast:
                    assistant_texts.append(cleaned_ast)
                if len(assistant_texts) >= 10:
                    break
    except Exception:
        pass

    for ast_text in assistant_texts:
        if not ast_text:
            continue
        # If transcribed voice is a substring of assistant speech or vice-versa
        if clean_user in ast_text or ast_text in clean_user:
            return True
        # Check word overlap ratio (> 25% match with any recent Jarvis utterance means echo!)
        user_words = set(clean_user.split())
        ast_words = set(ast_text.split())
        if user_words and ast_words:
            overlap = len(user_words.intersection(ast_words)) / len(user_words)
            if overlap >= 0.25:
                return True

    # 2. If recorded while speaking or within 5.0 seconds of speech ending, strictly require explicit interrupt command
    if is_speaking or time_since_speech < 5.0:
        strict_interrupt_keywords = ["stop", "cancel", "halt", "pause", "quiet", "shut up", "jarvis stop"]
        if not any(kw in clean_user for kw in strict_interrupt_keywords):
            return True  # Treat as self-echo and ignore

    return False

async def main():
    """Main program loop with intelligent request handling"""
    global jarvis_is_speaking
    
    show_startup_banner()

    # Initialize speech recognition elements
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = config.DYNAMIC_ENERGY
    recognizer.energy_threshold = config.ENERGY_THRESHOLD
    recognizer.pause_threshold = getattr(config, 'PAUSE_THRESHOLD', 0.8)
    recognizer.phrase_threshold = getattr(config, 'PHRASE_THRESHOLD', 0.3)

    try:
        mics = sr.Microphone.list_microphone_names()
        has_mic = len(mics) > 0
    except Exception:
        has_mic = False

    microphone = None
    if has_mic:
        try:
            microphone = sr.Microphone()
            # Do not open the mic stream here to prevent context manager conflicts with the background thread.
            console.print("[bold green]System:[/] Microphone initialized. [bold cyan]Voice Input Active[/].")
        except Exception as e:
            console.print(f"[bold red]System:[/] Microphone initialization failed: {e}. Fallback to Text Only.")
            has_mic = False

    # Start console input thread
    console.print("[bold green]System:[/] Keyboard listener active. [bold cyan]Text Input Active[/].")
    console.print("[bold white]Note:[/] You can speak or type at any time. To type, just type your query and press Enter.\n")
    threading.Thread(target=console_input_thread, daemon=True).start()

    # Play greeting immediately so user gets feedback instantly
    greeting = "Online and ready, sir."
    await speak_jarvis(greeting)

    # Define background audio listener callback
    def audio_callback(rec, audio):
        # Drop older unprocessed audio packets so we always take the latest speech immediately
        with input_queue.mutex:
            input_queue.queue.clear()
        input_queue.put(("voice", audio))

    stop_listening = None
    if has_mic and microphone:
        # Calibrate to ambient noise to set the threshold dynamically above background noise
        with console.status("[yellow]Calibrating microphone to room noise...[/]"):
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
        # Start listening in background (runs continuously)
        stop_listening = recognizer.listen_in_background(microphone, audio_callback)

    # Start the proactive background reminder scheduler
    scheduler_task = asyncio.create_task(start_reminder_scheduler())
    # Start background dashboard updater
    dashboard_updater = asyncio.create_task(dashboard_data_writer_task())

    while True:
        try:
            # Wait asynchronously for either voice or text input from the queue
            input_type, data = await asyncio.to_thread(input_queue.get)

            if input_type == "system" and data == "exit":
                raise KeyboardInterrupt

            user_text_str = ""

            if input_type == "text":
                from audio.tts import stop_tts
                stop_tts()
                user_text_str = data
                console.print(f"\n[bold green]Sir (Typed):[/] {user_text_str}")
            elif input_type == "voice":
                # Transcribe speech first to check for validity before interrupting current actions
                with console.status("[yellow]Processing voice...[/]"):
                    user_text = transcribe_audio(data)

                if not user_text or len(str(user_text).strip()) < 2:
                    continue

                user_text_str = str(user_text).strip()

                # SELF-ECHO FILTERING - Ignore mic picking up Jarvis's own speakers
                if is_self_echo(user_text_str):
                    continue

                # NOISE FILTERING - Check if input is background noise or unwanted phrase
                cleaned_text = user_text_str.lower().replace(".", "").replace(",", "")
                is_noise = any(
                    cleaned_text == noise.lower().replace(".", "").replace(",", "")
                    for noise in config.NOISE_WORDS
                )

                if is_noise:
                    continue

            # Wake word and session checking BEFORE interrupting or setting jarvis_is_speaking
            wake_words = getattr(config, 'WAKE_WORDS', [])
            is_addressed = any(word.lower() in user_text_str.lower() for word in wake_words)

            # Check if waiting for response to a question
            last_message_was_question = False
            if len(messages) > 1 and messages[-1]["role"] == "assistant":
                last_content = messages[-1]["content"].rsplit(']', maxsplit=1)[-1].strip()
                last_content = re.sub(r"\[\[UPDATE_SCHEDULE:.*?\]\]", "", last_content, flags=re.DOTALL).strip()
                if last_content.endswith('?'):
                    last_message_was_question = True

            # Decision logic with intelligent context
            should_process = (
                input_type == "text" # Always process typed text immediately
                or not config.REQUIRE_WAKE_WORD
                or is_addressed
                or last_message_was_question
            )

            if not should_process:
                continue

            # ONLY IF valid speech passed noise and wake-word checks: interrupt current TTS speech now!
            if input_type == "voice":
                from audio.tts import stop_tts
                stop_tts()
                console.print(f"\n[bold green]Sir (Spoken):[/] {user_text_str}")

            # Set flag to True to block background audio queueing during processing
            jarvis_is_speaking = True

            # INTELLIGENT REQUEST ANALYSIS PHASE
            request_complexity, _ = analyze_request_complexity(user_text_str)

            # AI RESPONSE PHASE (handles intermediate & final speech internally)
            response = await get_jarvis_response(user_text_str, request_complexity)

            if "[IGNORE]" in response or "[SKIP]" in response:
                jarvis_is_speaking = False
                continue

            # Finished speaking and processing (handled inside get_jarvis_response)
            jarvis_is_speaking = False

        except KeyboardInterrupt:
            closing = "Powering down. Have a pleasant day, sir."
            console.print(f"\n[cyan]Jarvis:[/] {closing}")
            await speak_jarvis(closing)
            # Cancel reminder task
            scheduler_task.cancel()
            dashboard_updater.cancel()
            # Stop background listener if running
            if stop_listening:
                stop_listening(wait_for_stop=False)
            # Run reflection before shutting down
            await run_reflection()
            # Final music cleanup on shutdown
            stop_music()
            from tools.dashboard_manager import hide_dashboard
            hide_dashboard()
            break
        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[bold red]Critical System Error:[/] {e}")
            await speak_jarvis("Sir, my systems have encountered a critical failure.")
            jarvis_is_speaking = False
            await asyncio.sleep(1)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except (EOFError, KeyboardInterrupt):
        pass
