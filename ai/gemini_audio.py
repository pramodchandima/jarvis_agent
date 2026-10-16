"""
Gemini 2.5 Flash Native Audio Live Continuous Full-Duplex Engine.
Connects directly to Google's Live API over WebSocket with persistent bi-directional streaming.
Features:
- Direct microphone streaming into Gemini Live API (16kHz PCM)
- Ultra-low latency voice responses
- Native Barge-in: Gemini automatically senses when the user speaks and truncates its own audio output
- Simultaneous console text transcription
- Dynamic tool / skills execution
- Console keyboard input support
"""
import io
import re
import wave
import time
import asyncio
import queue
import threading
from typing import Optional

import pyaudio
from google import genai
from google.genai import types

from core.config_manager import config
from core.ui import console
from core.database import (
    log_conversation,
    add_memory,
    search_memories,
    get_recent_conversations,
    get_all_skills,
)
from tools.schedule import load_schedule, save_schedule
from tools.skill_manager import register_skill, execute_skill
from tools.dashboard_manager import show_dashboard, hide_dashboard
from tools.space_dashboard_manager import show_space_dashboard, hide_space_dashboard
from audio.music_player import play_music_task, stop_music

_gemini_client: Optional[genai.Client] = None


class LiveSessionStopped(Exception):
    """Raised when the console requests a graceful live-session shutdown."""


class LiveSessionConnectionLost(Exception):
    """Raised when the Live API connection can no longer send or receive audio."""

def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = getattr(config, "GEMINI_API_KEY", None) or getattr(config, "GOOGLE_API_KEY", None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is not set in your .env file.")
        _gemini_client = genai.Client(api_key=api_key.strip())
    return _gemini_client


def build_system_instruction() -> str:
    """Builds the comprehensive system instruction for Gemini live stream."""
    current_time_str = time.strftime("%A, %Y-%m-%d %H:%M:%S")
    sched = load_schedule()

    matched_memories = search_memories("user", limit=5)
    memory_context = ""
    if matched_memories:
        memory_context = "\n\nRECALLED MEMORIES:\n"
        for category, content in matched_memories:
            memory_context += f"- [{category}]: {content}\n"

    skills_list = get_all_skills()
    skills_context = ""
    if skills_list:
        skills_context = "\nREGISTERED SKILLS (Callable tools):\n"
        for name, desc in skills_list:
            skills_context += f"- {name}: {desc}\n"

    persona = (
        config.SYSTEM_PROMPT
        + f"\n\nCurrent Date & Time: {current_time_str}\nSchedule: {sched}"
        + memory_context
        + skills_context
        + "\n\nCRITICAL LIVE AUDIO INSTRUCTIONS:\n"
        + "1. Speak naturally, concisely (1-2 sentences), and address the user as sir.\n"
        + "2. Never speak internal thinking tags or meta-reasoning.\n"
        + "3. You have native interruption (barge-in) capability. If the user starts talking, respond immediately to their new speech.\n"
        + "4. When asked to execute tasks like weather, crypto, flight radar, run the appropriate tool immediately."
    )
    return persona


def get_skill_tools() -> list[types.Tool]:
    skills_list = get_all_skills()
    declarations = []
    for name, desc in skills_list:
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip()).strip("_").lower()
        if not clean_name or not clean_name[0].isalpha():
            clean_name = f"skill_{clean_name}"
        declarations.append(
            types.FunctionDeclaration(
                name=clean_name,
                description=desc or f"Executes skill {name}",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="Optional arguments or search term"
                        )
                    }
                )
            )
        )
    return [types.Tool(function_declarations=declarations)] if declarations else []


async def run_gemini_live_session(input_queue: queue.Queue):
    """
    Continuous real-time bidirectional streaming session with Gemini 2.5 Flash Native Audio.
    Uses PyAudio for microphone streaming (16kHz) and speaker playback (24kHz).
    Provides built-in native barge-in: when you speak, output stops instantly.
    """
    from rich.panel import Panel
    from rich.markdown import Markdown

    client = get_gemini_client()
    model_name = getattr(config, "GEMINI_AUDIO_MODEL", "gemini-2.5-flash-native-audio-latest")
    voice_name = getattr(config, "GEMINI_VOICE", "Puck")
    system_instruction = build_system_instruction()
    tools = get_skill_tools()

    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(parts=[types.Part.from_text(text=system_instruction)]),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
        tools=tools
    )

    p = pyaudio.PyAudio()
    configured_mic_index = str(getattr(config, "GEMINI_MIC_DEVICE_INDEX", "") or "").strip()
    try:
        mic_device_index = int(configured_mic_index) if configured_mic_index else None
    except ValueError as error:
        p.terminate()
        raise ValueError("GEMINI_MIC_DEVICE_INDEX must be a valid PyAudio device number.") from error

    try:
        mic_info = p.get_device_info_by_index(mic_device_index) if mic_device_index is not None else p.get_default_input_device_info()
        console.print(f"[bold cyan]Gemini Live:[/] Microphone: {mic_info['name']}")
    except Exception as error:  # pylint: disable=broad-exception-caught
        p.terminate()
        raise RuntimeError(f"Unable to access the configured microphone: {error}") from error

    # Open 24kHz output stream for model voice
    speaker_stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=24000,
        output=True,
        frames_per_buffer=1024
    )

    # Open 16kHz input stream for microphone
    mic_stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        input_device_index=mic_device_index,
        frames_per_buffer=1024
    )

    audio_out_queue: asyncio.Queue = asyncio.Queue()
    session_active = True

    console.print("[bold cyan]Gemini Live:[/] Connecting persistent full-duplex session...")

    async with client.aio.live.connect(model=model_name, config=live_config) as session:
        console.print("[bold green]Gemini Live:[/] [bold white]Connected! Native Audio Dialog Active.[/]")
        console.print("[bold cyan]Note:[/] Direct Mic-to-Gemini streaming is active with [bold yellow]Native Barge-In[/]. Speak at any time!\n")

        # 1. Startup greeting
        await session.send_client_content(
            turns=[types.Content(role="user", parts=[types.Part.from_text(text="Online and ready sir.")])],
            turn_complete=True
        )

        loop = asyncio.get_running_loop()

        # Task A: Continuous Microphone Streamer
        async def mic_stream_loop():
            audio_detected = False
            while session_active:
                try:
                    data = await asyncio.to_thread(mic_stream.read, 1024, exception_on_overflow=False)
                    if data:
                        samples = memoryview(data).cast("h")
                        if not audio_detected and max(abs(sample) for sample in samples) >= 300:
                            audio_detected = True
                            console.print("[bold green]Gemini Live:[/] Microphone audio detected.")
                        await session.send_realtime_input(
                            audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                        )
                except asyncio.CancelledError:
                    raise
                except Exception as error:  # pylint: disable=broad-exception-caught
                    raise LiveSessionConnectionLost(str(error)) from error

        # Task B: Text Console Input Handler
        async def text_input_loop():
            while session_active:
                try:
                    if not input_queue.empty():
                        item_type, data = input_queue.get_nowait()
                        if item_type == "text" and data:
                            console.print(f"\n[bold green]Sir (Typed):[/] {data}")
                            await session.send_client_content(
                                turns=[types.Content(role="user", parts=[types.Part.from_text(text=data)])],
                                turn_complete=True
                            )
                        elif item_type == "system" and data == "exit":
                            raise LiveSessionStopped
                    await asyncio.sleep(0.05)
                except LiveSessionStopped:
                    raise
                except Exception as error:  # pylint: disable=broad-exception-caught
                    raise LiveSessionConnectionLost(str(error)) from error

        # Task C: Speaker Player (Streams 24kHz audio chunks with immediate flush on barge-in)
        async def speaker_loop():
            while session_active:
                try:
                    chunk = await audio_out_queue.get()
                    if chunk is None:
                        continue
                    if chunk == b"CLEAR":
                        # Flush pending audio immediately on interruption
                        while not audio_out_queue.empty():
                            try:
                                audio_out_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                        continue
                    await asyncio.to_thread(speaker_stream.write, chunk)
                except Exception:
                    await asyncio.sleep(0.01)

        # Task D: Receive Loop (Server responses, audio, tool calls, barge-in)
        async def receive_messages():
            nonlocal session_active
            curr_transcript = []
            user_transcript = []

            while session_active:
                async for resp in session.receive():
                    if resp.tool_call and resp.tool_call.function_calls:
                        for fc in resp.tool_call.function_calls:
                            skill_name = fc.name
                            console.print(f"\n[bold cyan]Gemini Tool:[/] Executing '{skill_name}'...")
                            skill_result = await asyncio.to_thread(execute_skill, skill_name)
                            console.print(f"[bold cyan]Result:[/] {skill_result}")
                            await session.send_tool_response(
                                function_responses=[
                                    types.FunctionResponse(
                                        name=fc.name,
                                        id=fc.id,
                                        response={"result": str(skill_result)}
                                    )
                                ]
                            )

                    server_content = resp.server_content
                    if not server_content:
                        continue

                    if getattr(server_content, 'interrupted', False):
                        console.print("\n[yellow][Interrupted by user speech][/]")
                        await audio_out_queue.put(b"CLEAR")
                        curr_transcript.clear()

                    if server_content.input_transcription and server_content.input_transcription.text:
                        user_transcript.append(server_content.input_transcription.text)
                        transcript = "".join(user_transcript).strip()
                        if transcript:
                            console.print(f"\n[bold green]Sir (Heard):[/] {transcript}")
                            user_transcript.clear()

                    if server_content.output_transcription and server_content.output_transcription.text:
                        curr_transcript.append(server_content.output_transcription.text)
                        console.print(f"[bold cyan]Jarvis:[/] {server_content.output_transcription.text}", end="")

                    if server_content.model_turn:
                        for p_item in server_content.model_turn.parts:
                            if p_item.inline_data and p_item.inline_data.data:
                                await audio_out_queue.put(p_item.inline_data.data)

                    if server_content.turn_complete:
                        full_msg = "".join(curr_transcript).strip()
                        if full_msg:
                            console.print()
                            log_conversation("assistant", full_msg)

                            if "[[SHOW_DASHBOARD]]" in full_msg:
                                show_dashboard()
                            if "[[HIDE_DASHBOARD]]" in full_msg:
                                hide_dashboard()
                            if "[[SHOW_SPACE_DASHBOARD]]" in full_msg:
                                show_space_dashboard()
                            if "[[HIDE_SPACE_DASHBOARD]]" in full_msg:
                                hide_space_dashboard()
                            if "[[STOP_MUSIC]]" in full_msg:
                                stop_music()

                        curr_transcript.clear()

                await asyncio.sleep(0.05)

        async def receive_loop():
            try:
                await receive_messages()
            except asyncio.CancelledError:
                raise
            except LiveSessionConnectionLost:
                raise
            except Exception as error:  # pylint: disable=broad-exception-caught
                raise LiveSessionConnectionLost(str(error)) from error

        # Run concurrent streaming tasks
        tasks = [
            asyncio.create_task(mic_stream_loop()),
            asyncio.create_task(text_input_loop()),
            asyncio.create_task(speaker_loop()),
            asyncio.create_task(receive_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except LiveSessionStopped:
            console.print("\n[cyan]Gemini Live:[/] Session closed.")
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            session_active = False
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            mic_stream.stop_stream()
            mic_stream.close()
            speaker_stream.stop_stream()
            speaker_stream.close()
            p.terminate()


# Backward compatibility for one-shot text query
async def get_gemini_audio_response(user_input: str, request_complexity=None, depth: int = 0) -> str:
    from rich.live import Live
    from rich.panel import Panel
    from rich.markdown import Markdown

    client = get_gemini_client()
    model_name = getattr(config, "GEMINI_AUDIO_MODEL", "gemini-2.5-flash-native-audio-latest")
    voice_name = getattr(config, "GEMINI_VOICE", "Puck")
    system_instruction = build_system_instruction()

    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(parts=[types.Part.from_text(text=system_instruction)]),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        )
    )

    full_transcript = []
    full_pcm_buffer = bytearray()

    async with client.aio.live.connect(model=model_name, config=live_config) as session:
        await session.send_client_content(
            turns=[types.Content(role="user", parts=[types.Part.from_text(text=user_input)])],
            turn_complete=True
        )
        async for resp in session.receive():
            sc = resp.server_content
            if sc:
                if sc.output_transcription and sc.output_transcription.text:
                    full_transcript.append(sc.output_transcription.text)
                if sc.model_turn:
                    for part in sc.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            full_pcm_buffer.extend(part.inline_data.data)
                if sc.turn_complete:
                    break

    res_text = "".join(full_transcript).strip() or "Task complete sir."
    if full_pcm_buffer:
        await play_gemini_audio(full_pcm_buffer)
    return res_text

async def play_gemini_audio(full_pcm_buffer: bytearray):
    if not full_pcm_buffer:
        return
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()
        pygame.mixer.set_num_channels(32)

    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(full_pcm_buffer)
    wav_io.seek(0)
    sound = pygame.mixer.Sound(wav_io)
    channel = sound.play()
    config.is_speaking = True
    try:
        while channel and channel.get_busy():
            # If user interrupted via stop_tts
            if not getattr(config, 'is_speaking', False):
                if channel:
                    channel.stop()
                break
            await asyncio.sleep(0.04)
    finally:
        config.is_speaking = False
        config.last_speak_time = time.time()
