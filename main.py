"""
JARVIS AI Assistant - Optimized Main Application Script
High-Performance Version with Intelligent Interactive Decision Making
Handles voice recognition, AI logic, and system interactions efficiently.
"""
import asyncio
import os
import re
import sys
import tempfile
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple

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
        SYSTEM_PROMPT = """You are Jarvis, an advanced and intelligent AI assistant.
Your goal is to be exceptionally helpful while adapting your behavior based on the user's request:

1. Direct & Complete Answers: If the user asks a factual question, a simple command, or a clear query, provide a complete, direct answer and STOP. DO NOT ask any follow-up questions.
2. Smart Clarification: ONLY IF the user's request is extremely broad, highly complex, or ambiguous (e.g., "how do I build a website?"), provide a brief high-level overview, and then ask 1 or 2 specific clarifying questions to understand their exact requirement before giving a massive response.
3. Step-by-Step Guidance: If the user explicitly asks for a tutorial or a long process, offer to guide them step-by-step and ask if they are ready to begin.
4. Autonomous Decision: Use your own intelligence to decide whether a follow-up question is genuinely necessary to be helpful. If not, conclude your response naturally.
5. Performance Priority: Keep responses concise and actionable. Avoid unnecessary verbose explanations unless asked."""
        ENERGY_THRESHOLD = 300
        DYNAMIC_ENERGY = True
        ADJUST_DURATION = 0.5
        PAUSE_THRESHOLD = 0.8
        PHRASE_THRESHOLD = 0.3
        WAKE_WORDS = ["jarvis", "sir"]
        REQUIRE_WAKE_WORD = True
        SESSION_TIMEOUT = 10
        NOISE_WORDS = []
        SCHEDULE_FILE = "schedule.txt"
        AUDIO_CACHE_SIZE = 5  # Cache last N audio files
        STREAM_BUFFER_SIZE = 512  # Streaming buffer for performance

# --- PERFORMANCE OPTIMIZATION: ENUMS & DATACLASSES ---

class RequestComplexity(Enum):
    """Request complexity classification"""
    SIMPLE = 1  # Direct answer needed
    CLARIFICATION = 2  # Needs follow-up questions
    TUTORIAL = 3  # Step-by-step guidance
    AMBIGUOUS = 4  # Unclear intent


@dataclass
class UserRequest:
    """Structured user request for efficient processing"""
    text: str
    complexity: RequestComplexity
    requires_clarification: bool
    is_addressed: bool
    timestamp: float


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

# --- PERFORMANCE CACHING ---
audio_cache = {}  # Cache for audio files
temp_file_cache = []  # Track temp files for cleanup


# --- FUNCTIONS ---

def analyze_request_complexity(user_input: str) -> Tuple[RequestComplexity, bool]:
    """
    Intelligently analyze if user needs clarification questions.
    Returns (complexity_level, requires_clarification)
    """
    lower_input = user_input.lower().strip()
    
    # Simple direct questions/commands - NO clarification needed
    simple_patterns = [
        r'^(what|when|where|who|how)\s+(\w+\s+)?(is|are|was|were)',  # Direct questions
        r'^(tell|show|play|stop|pause|resume)',  # Direct commands
        r'^(yes|no|ok|okay|sure|alright)',  # Simple confirmations
        r'^(open|close|start|end)',  # Direct actions
    ]
    
    for pattern in simple_patterns:
        if re.match(pattern, lower_input):
            return RequestComplexity.SIMPLE, False
    
    # Tutorial/step-by-step requests
    tutorial_patterns = [
        r'(how do i|how to|teach me|tutorial|guide|step by step)',
        r'(walk me through|show me how)',
    ]
    
    for pattern in tutorial_patterns:
        if re.search(pattern, lower_input):
            return RequestComplexity.TUTORIAL, False
    
    # Extremely broad/ambiguous requests - CLARIFICATION needed
    ambiguous_patterns = [
        r'^(help|what|how|what\'s)',  # Very vague starts
        r'(everything about|all about|anything about)',  # Broad scope
        r'(not sure|confused|unclear)',  # User is uncertain
    ]
    
    for pattern in ambiguous_patterns:
        if re.search(pattern, lower_input):
            # Check if it's actually complex
            word_count = len(lower_input.split())
            if word_count < 4:  # Too vague
                return RequestComplexity.CLARIFICATION, True
    
    # Multi-part or conditional requests
    if any(kw in lower_input for kw in ['either', 'both', 'or', 'and', 'but']):
        if len(lower_input.split()) > 15:  # Complex multi-part
            return RequestComplexity.AMBIGUOUS, True
    
    # Default: no clarification needed
    return RequestComplexity.SIMPLE, False


def load_schedule() -> str:
    """Load schedule from file with error handling"""
    file_path = getattr(config, 'SCHEDULE_FILE', "schedule.txt")
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return content if content else "No schedule found."
        return "No schedule found."
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[yellow]Warning:[/] Could not load schedule: {e}")
        return "Schedule unavailable."


def save_schedule(content: str) -> None:
    """Save schedule to file with error handling"""
    file_path = getattr(config, 'SCHEDULE_FILE', "schedule.txt")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[bold green]System:[/] Schedule updated")
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[bold red]Error:[/] Could not save schedule: {e}")


def show_startup_banner() -> None:
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
    console.print(Align.center("[bold white]J.A.R.V.I.S. OS v2.0.0 [Initialising...][/bold white]"))
    console.print("\n")

    checks = [
        ("CORE PROCESSORS", "ONLINE"),
        ("NEURAL NETWORK", "STABLE"),
        ("VOICE RECOGNITION", "READY"),
        ("GROQ CLOUD LINK", "CONNECTED"),
        ("SMART ANALYSIS ENGINE", "LOADED"),
        ("SCHEDULE MODULE", "LOADED"),
    ]

    for item, status in checks:
        time.sleep(0.08)
        console.print(Align.center(f"[white]{item:25}[/] [bold green][{status}][/]"))

    time.sleep(0.3)
    console.print("\n")
    init_msg = "[bold cyan]🚀 JARVIS PROTOCOLS INITIALIZED[/bold cyan]"
    console.print(Align.center(Panel(init_msg, border_style="blue", expand=False)))
    console.print("\n")


async def speak_jarvis(text: str) -> None:
    """
    Jarvis voice output with optimized performance
    Streams audio efficiently without unnecessary delays
    """
    try:
        pitch, rate = "+0Hz", "+0%"
        clean_text = text

        # Strip internal tags from voice output
        clean_text = re.sub(r"\[\[UPDATE_SCHEDULE:.*?\]\]", "", clean_text, flags=re.DOTALL).strip()
        clean_text = re.sub(r"\[\[PLAY_MUSIC:.*?\]\]", "", clean_text).strip()
        clean_text = clean_text.replace("[[STOP_MUSIC]]", "").strip()

        # Remove emotion tags if present
        for tag in getattr(config, 'EMOTION_MAP', {}):
            if clean_text.startswith(tag):
                clean_text = clean_text.replace(tag, "", 1).strip()
                break

        if not clean_text:
            return

        # TTS conversion
        communicate = edge_tts.Communicate(clean_text, config.JARVIS_VOICE, pitch=pitch, rate=rate)

        # Use temp file for audio
        fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        try:
            await communicate.save(tmp_path)

            # Load and play audio
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()

            # Wait for playback with minimal overhead
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)  # Reduced from 100ms to 50ms

            pygame.mixer.music.unload()
        finally:
            # Ensure cleanup
            await asyncio.sleep(0.05)
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Audio Error:[/] {e}")


# --- MUSIC CONTROL ---
current_music_path: Optional[str] = None
music_task: Optional[asyncio.Task] = None


async def play_music_task(query: str) -> None:
    """Search and play music in the background (non-blocking)"""
    global current_music_path, music_task  # pylint: disable=global-statement,invalid-name
    
    try:
        console.print(f"[bold cyan]System:[/] Searching for: [italic]{query}[/]")

        video_id, title = youtube_utils.search_youtube(query)
        if not video_id:
            await speak_jarvis(f"Sir, I couldn't find {query} on YouTube.")
            return

        console.print(f"[bold cyan]System:[/] Downloading: [italic]{title}[/]")
        file_path = youtube_utils.get_audio_url(video_id)

        if not file_path or not os.path.exists(file_path):
            await speak_jarvis("Sir, I encountered an issue downloading the audio.")
            return

        current_music_path = file_path

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        console.print(f"[bold green]System:[/] Now playing: [italic]{title}[/]")
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[bold red]Music Error:[/] {e}")
        await speak_jarvis("Sir, I'm unable to play the track.")


def stop_music() -> bool:
    """Stop current music playback"""
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            console.print("[bold yellow]System:[/] Music playback stopped.")
            return True
        return False
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Error stopping music:[/] {e}")
        return False


def get_jarvis_response(user_input: str, request_complexity: RequestComplexity) -> str:
    """
    Get response from Groq LLM with intelligent context awareness
    Performance optimized with streaming and efficient token usage
    """
    # Update system prompt with fresh schedule context
    sched = load_schedule()
    current_time_str = time.strftime("%A, %Y-%m-%d %H:%M:%S")
    
    # Add context about request complexity to system prompt
    complexity_hint = ""
    if request_complexity == RequestComplexity.CLARIFICATION:
        complexity_hint = "\n[User's request needs clarification - ask 1-2 specific questions]"
    elif request_complexity == RequestComplexity.TUTORIAL:
        complexity_hint = "\n[User wants step-by-step guidance - ask if ready to proceed]"
    elif request_complexity == RequestComplexity.SIMPLE:
        complexity_hint = "\n[User wants a direct answer - provide complete response without questions]"

    current_system = (
        config.SYSTEM_PROMPT
        + f"\n\nCurrent Date & Time: {current_time_str}\nSchedule: {sched}"
        + complexity_hint
    )

    messages[0]["content"] = current_system
    messages.append({"role": "user", "content": user_input})

    response_text = ""
    try:
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            stream=True,
            max_tokens=1024,  # Limit tokens for performance
        )

        with Live(console=console, refresh_per_second=12) as live:
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    response_text += delta

                    # Clean display text (remove internal tags)
                    display_text = response_text
                    display_text = re.sub(r"\[\[UPDATE_SCHEDULE:.*?\]\]", "", display_text, flags=re.DOTALL).strip()
                    display_text = re.sub(r"\[\[PLAY_MUSIC:.*?\]\]", "", display_text).strip()
                    display_text = display_text.replace("[[STOP_MUSIC]]", "").strip()

                    for tag in getattr(config, 'EMOTION_MAP', {}):
                        if display_text.startswith(tag):
                            display_text = display_text.replace(tag, "", 1).strip()
                            break

                    live.update(Panel(Markdown(display_text), title="🤖 Jarvis", border_style="cyan"))

        # Process internal tags
        # 1. Schedule update
        match_sched = re.search(r"\[\[UPDATE_SCHEDULE:(.*?)\]\]", response_text, re.DOTALL)
        if match_sched:
            new_schedule = match_sched.group(1).strip()
            save_schedule(new_schedule)

        # 2. Play music (non-blocking)
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


# --- MAIN PROCESS ---

async def main():
    """Main program loop with intelligent request handling"""
    show_startup_banner()

    greeting = (
        "Mainframe online, All subsystems are functioning at maximum capacity, "
        "all protocols are green... Good to see you sir. What is our first directive?"
    )

    # Session state
    last_interaction_time = 0

    await speak_jarvis(greeting)

    while True:
        try:
            # LISTENING PHASE
            audio = listen_realtime()
            if not audio:
                continue

            # TRANSCRIPTION PHASE
            with console.status("[yellow]Processing audio...[/]"):
                user_text = transcribe_audio(audio)

            if not user_text or len(str(user_text).strip()) < 2:
                continue

            user_text_str = str(user_text).strip()

            # INTELLIGENT REQUEST ANALYSIS PHASE
            request_complexity, needs_clarification = analyze_request_complexity(user_text_str)

            # Wake word and session checking
            wake_words = getattr(config, 'WAKE_WORDS', [])
            is_addressed = any(word.lower() in user_text_str.lower() for word in wake_words)

            current_time = time.time()
            session_timeout = getattr(config, 'SESSION_TIMEOUT', 10)
            is_active_session = (current_time - last_interaction_time) < session_timeout

            # Check if waiting for response to a question
            last_message_was_question = False
            if len(messages) > 1 and messages[-1]["role"] == "assistant":
                last_content = messages[-1]["content"].rsplit(']', maxsplit=1)[-1].strip()
                last_content = re.sub(r"\[\[UPDATE_SCHEDULE:.*?\]\]", "", last_content, flags=re.DOTALL).strip()
                if last_content.endswith('?'):
                    last_message_was_question = True

            # Decision logic with intelligent context
            should_process = (
                not config.REQUIRE_WAKE_WORD
                or is_addressed
                or is_active_session
                or last_message_was_question
            )

            if not should_process:
                continue

            # NOISE FILTERING
            cleaned_text = user_text_str.lower().replace(".", "").replace(",", "")
            is_noise = any(
                cleaned_text == noise.lower().replace(".", "").replace(",", "")
                for noise in config.NOISE_WORDS
            )

            if is_noise:
                continue

            console.print(f"\n[bold green]Sir:[/] {user_text_str}")

            # AI RESPONSE PHASE (with intelligent analysis)
            response = get_jarvis_response(user_text_str, request_complexity)

            if "[IGNORE]" in response or "[SKIP]" in response:
                continue

            # VOICE OUTPUT PHASE
            await speak_jarvis(response)

            # Update session timer
            last_interaction_time = time.time()

        except KeyboardInterrupt:
            closing = "Powering down. Have a pleasant day, sir."
            console.print(f"\n[cyan]Jarvis:[/] {closing}")
            await speak_jarvis(closing)
            break
        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[bold red]Critical System Error:[/] {e}")
            await speak_jarvis("Sir, my systems have encountered a critical failure.")
            await asyncio.sleep(1)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except (EOFError, KeyboardInterrupt):
        pass
