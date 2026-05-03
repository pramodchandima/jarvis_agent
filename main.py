"""
JARVIS AI Assistant - Main Application Script
Handles voice recognition, AI logic, and system interactions.
"""
import asyncio
import os
import re
import sys
import tempfile
import time

import edge_tts
import pygame
import speech_recognition as sr
from groq import Groq
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

import youtube_utils

# Import configuration
try:
    import config
except ImportError:
    class config:  # pylint: disable=invalid-name
        """Fallback configuration if config.py is missing"""
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        LLM_MODEL = "llama-3.3-70b-versatile"
        TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
        JARVIS_VOICE = "en-GB-RyanNeural"
        SYSTEM_PROMPT = "You are Jarvis."
        ENERGY_THRESHOLD = 300
        DYNAMIC_ENERGY = True
        ADJUST_DURATION = 0.5
        WAKE_WORDS = ["jarvis", "sir"]
        REQUIRE_WAKE_WORD = True
        SESSION_TIMEOUT = 10
        NOISE_WORDS = []
        SCHEDULE_FILE = "schedule.txt"

# --- INITIALIZATION ---
console = Console()

if not config.GROQ_API_KEY:
    console.print(
        "[bold red]Error:[/] GROQ_API_KEY not found in config.py or environment variables."
    )
    sys.exit(1)

client = Groq(api_key=config.GROQ_API_KEY.strip())
pygame.mixer.init()

messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]

# --- FUNCTIONS ---

def load_schedule():
    """Load schedule from file"""
    file_path = getattr(config, 'SCHEDULE_FILE', "schedule.txt")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "No schedule found."

def save_schedule(content):
    """Save schedule to file"""
    file_path = getattr(config, 'SCHEDULE_FILE', "schedule.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    console.print(f"[bold green]System:[/] Schedule updated in {file_path}")

def show_startup_banner():
    """Display a cool JARVIS startup banner"""
    console.clear()

    jarvis_art = r"""
[bold cyan]
       _   _    ___  __     __ ___  ____
      | | / \  |  _ \ \ \   / /|_ _/ ___|
   _  | |/ _ \ | |_) | \ \ / /  | |\___ \
  | |_| / ___ \|  _ <   \ V /   | | ___) |
    \___/_/   \_\_| \_\   \_/   |___|____/
[/bold cyan]
    """

    console.print(Align.center(jarvis_art))
    console.print(Align.center("[bold white]J.A.R.V.I.S. OS v1.2.0 [Initialising...][/bold white]"))
    console.print("\n")

    checks = [
        ("CORE PROCESSORS", "ONLINE"),
        ("NEURAL NETWORK", "STABLE"),
        ("VOICE RECOGNITION", "READY"),
        ("GROQ CLOUD LINK", "CONNECTED"),
        ("SCHEDULE MODULE", "LOADED"),
    ]

    for item, status in checks:
        time.sleep(0.1)
        console.print(Align.center(f"[white]{item:20}[/] [bold green][{status}][/]"))

    time.sleep(0.3)
    console.print("\n")
    init_msg = "[bold cyan]🚀 JARVIS PROTOCOLS INITIALIZED[/bold cyan]"
    console.print(Align.center(Panel(init_msg, border_style="blue", expand=False)))
    console.print("\n")

async def speak_jarvis(text: str):
    """Jarvis voice output with dynamic emotion-based pitch and rate"""
    try:
        pitch, rate = "+0Hz", "+0%"
        clean_text = text

        # Strip schedule update tags and emotion tags from voice
        clean_text = re.sub(r"\[\[UPDATE_SCHEDULE:.*?\]\]", "", clean_text, flags=re.DOTALL).strip()

        for tag, settings in getattr(config, 'EMOTION_MAP', {}).items():
            if clean_text.startswith(tag):
                pitch, rate = settings
                clean_text = clean_text.replace(tag, "", 1).strip()
                break

        # New: Strip music tags
        clean_text = re.sub(r"\[\[PLAY_MUSIC:.*?\]\]", "", clean_text).strip()
        clean_text = clean_text.replace("[[STOP_MUSIC]]", "").strip()

        if not clean_text:
            return

        communicate = edge_tts.Communicate(clean_text, config.JARVIS_VOICE, pitch=pitch, rate=rate)

        fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        await communicate.save(tmp_path)

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)

        pygame.mixer.music.unload()
        await asyncio.sleep(0.1)

        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Audio Error:[/] {e}")

# --- MUSIC CONTROL ---
current_music_path = None  # pylint: disable=invalid-name

async def play_music_task(query):
    """Search and play music in the background"""
    global current_music_path  # pylint: disable=global-statement,invalid-name
    console.print(f"[bold cyan]System:[/] Searching YouTube for: [italic]{query}[/]")

    video_id, title = youtube_utils.search_youtube(query)
    if not video_id:
        console.print(f"[bold red]Music Error:[/] {title}")
        await speak_jarvis(f"Sir, I couldn't find {query} on YouTube.")
        return

    console.print(f"[bold cyan]System:[/] Downloading and preparing: [italic]{title}[/]")
    file_path = youtube_utils.get_audio_url(video_id)

    if not file_path or not os.path.exists(file_path):
        console.print("[bold red]Music Error:[/] Failed to download audio.")
        await speak_jarvis("Sir, I encountered an issue downloading the audio.")
        return

    current_music_path = file_path

    try:
        # Stop any existing music
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        console.print(f"[bold green]System:[/] Now playing: [italic]{title}[/]")
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[bold red]Playback Error:[/] {e}")
        await speak_jarvis("Sir, I'm unable to play the track.")

def stop_music():
    """Stop current music playback"""
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
        console.print("[bold yellow]System:[/] Music playback stopped.")
        return True
    return False

def get_jarvis_response(user_input: str):
    """Get response from Groq LLM with schedule awareness"""

    # Update system prompt with fresh schedule context and current date/time
    sched = load_schedule()
    current_time_str = time.strftime("%A, %Y-%m-%d %H:%M:%S")
    current_system = (
        f"{config.SYSTEM_PROMPT}\n\nCURRENT CONTEXT:\n- Date & Time: {current_time_str}"
        f"\n\nCURRENT SCHEDULE:\n{sched}"
    )
    messages[0]["content"] = current_system

    messages.append({"role": "user", "content": user_input})

    response_text = ""
    try:
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            stream=True,
        )

        with Live(console=console, refresh_per_second=15) as live:
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    response_text += delta

                    # UI display cleaning
                    display_text = response_text
                    # Hide internal tags
                    display_text = re.sub(
                        r"\[\[UPDATE_SCHEDULE:.*?\]\]", "", display_text, flags=re.DOTALL
                    ).strip()
                    display_text = re.sub(r"\[\[PLAY_MUSIC:.*?\]\]", "", display_text).strip()
                    display_text = display_text.replace("[[STOP_MUSIC]]", "").strip()

                    for tag in getattr(config, 'EMOTION_MAP', {}):
                        if display_text.startswith(tag):
                            display_text = display_text.replace(tag, "", 1).strip()
                            break

                    live.update(Panel(Markdown(display_text),
                                title="🤖 Jarvis", border_style="cyan"))

        # Process tags
        # 1. Schedule update
        match_sched = re.search(r"\[\[UPDATE_SCHEDULE:(.*?)\]\]", response_text, re.DOTALL)
        if match_sched:
            new_schedule = match_sched.group(1).strip()
            save_schedule(new_schedule)

        # 2. Play music
        match_play = re.search(r"\[\[PLAY_MUSIC:(.*?)\]\]", response_text)
        if match_play:
            query = match_play.group(1).strip()
            asyncio.create_task(play_music_task(query))

        # 3. Stop music
        if "[[STOP_MUSIC]]" in response_text:
            stop_music()

        messages.append({"role": "assistant", "content": response_text})
        return response_text
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = f"Sir, I encountered an internal error: {e}"
        console.print(f"[bold red]LLM Error:[/] {e}")
        return error_msg

def listen_realtime():
    """VAD based listening using config settings"""
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = config.DYNAMIC_ENERGY
    recognizer.energy_threshold = config.ENERGY_THRESHOLD
    recognizer.pause_threshold = config.PAUSE_THRESHOLD
    recognizer.phrase_threshold = config.PHRASE_THRESHOLD

    with sr.Microphone() as source:
        console.print("\n[bold blue]Listening...[/] (At your service, sir)")
        try:
            recognizer.adjust_for_ambient_noise(source, duration=config.ADJUST_DURATION)
            audio = recognizer.listen(source, timeout=None, phrase_time_limit=None)
            return audio
        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[red]Microphone Error:[/] {e}")
            return None

def transcribe_audio(audio_data):
    """Whisper transcription using Groq API"""
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

# --- MAIN PROCESS ---

async def main():
    """Main program loop"""
    show_startup_banner()

    # Initial Greeting
    greeting = (
        "Mainframe online, All subsystems are functioning at maximum capacity, "
        "all protocols are green... Good to see you sir!!, What is our first directive today?"
    )

    # Session state
    last_interaction_time = 0

    await speak_jarvis(greeting)

    while True:
        try:
            # Listening phase
            audio = listen_realtime()
            if not audio:
                continue

            # Transcription phase
            with console.status("[yellow]Processing audio...[/]"):
                user_text = transcribe_audio(audio)

            if not user_text or len(str(user_text).strip()) < 2:
                continue

            # Check for wake words or active session
            user_text_str = str(user_text).strip()
            wake_words = getattr(config, 'WAKE_WORDS', [])
            is_addressed = any(word.lower() in user_text_str.lower() for word in wake_words)

            # active_session check
            current_time = time.time()
            session_timeout = getattr(config, 'SESSION_TIMEOUT', 12)
            is_active_session = (current_time - last_interaction_time) < session_timeout

            # Check if we are in the middle of a question flow
            last_message_was_question = False
            if len(messages) > 1 and messages[-1]["role"] == "assistant":
                last_content = messages[-1]["content"].rsplit(']', maxsplit=1)[-1].strip()
                last_content = re.sub(r"\[\[UPDATE_SCHEDULE:.*?\]\]", "", last_content,
                                     flags=re.DOTALL).strip()
                if last_content.endswith('?'):
                    last_message_was_question = True

            # Decide whether to process
            should_process = (
                not config.REQUIRE_WAKE_WORD or
                is_addressed or
                is_active_session or
                last_message_was_question
            )
            if not should_process:
                continue

            # Noise filtering
            cleaned_text = user_text_str.lower().replace(".", "").replace(",", "")
            is_noise = False
            for noise in config.NOISE_WORDS:
                if cleaned_text == noise.lower().replace(".", "").replace(",", ""):
                    is_noise = True
                    break

            if is_noise:
                continue

            console.print(f"\n[bold green]Sir:[/] {user_text_str}")

            # AI Response phase
            response = get_jarvis_response(user_text_str)

            if "[IGNORE]" in response or "[SKIP]" in response:
                continue

            # Voice Output phase
            await speak_jarvis(response)

            # Update session timer only on a valid response
            last_interaction_time = time.time()

        except KeyboardInterrupt:
            closing = "Powering down. Have a pleasant day, sir."
            console.print(f"\n[cyan]Jarvis:[/] {closing}")
            await speak_jarvis(closing)
            break
        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[bold red]Critical System Error:[/] {e}")
            await speak_jarvis("Sir, my systems have encountered a critical failure.")
            await asyncio.sleep(2)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except (EOFError, KeyboardInterrupt):
        pass
