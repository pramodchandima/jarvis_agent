import time
from rich.align import Align
from rich.console import Console
from rich.panel import Panel

console = Console()

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

    import os
    import socket
    import pygame
    import speech_recognition as sr
    from core.config_manager import config

    # 1. CORE PROCESSORS
    cores = os.cpu_count() or 1
    cpu_status = ("ONLINE", f"ONLINE ({cores} CORES)")

    # 2. NEURAL NETWORK
    audio_active = pygame.mixer.get_init() is not None
    nn_status = ("STABLE" if audio_active else "NO AUDIO DEV", "STABLE" if audio_active else "[bold red]NO AUDIO DEV[/]")

    # 3. VOICE RECOGNITION
    try:
        mics = sr.Microphone.list_microphone_names()
        mic_ok = len(mics) > 0
    except Exception:
        mic_ok = False
    voice_status = ("READY" if mic_ok else "NO MIC", "READY" if mic_ok else "[bold red]NO MIC FOUND[/]")

    # 4. ACTIVE AI ENGINE
    active_provider = getattr(config, 'AI_PROVIDER', 'groq').lower()
    if active_provider == "gemini":
        has_gemini_key = bool(getattr(config, 'GEMINI_API_KEY', None) or getattr(config, 'GOOGLE_API_KEY', None))
        ai_status = ("GEMINI 2.5 NATIVE", "[bold cyan]GEMINI 2.5 NATIVE AUDIO[/]" if has_gemini_key else "[bold red]GEMINI KEY MISSING[/]")
    else:
        has_groq_key = bool(config.GROQ_API_KEY)
        ai_status = ("GROQ + EDGE-TTS", "[bold magenta]GROQ + EDGE-TTS[/]" if has_groq_key else "[bold red]GROQ KEY MISSING[/]")

    # 5. SCHEDULE MODULE
    sched_path = getattr(config, 'SCHEDULE_FILE', "schedule.txt")
    has_sched = os.path.exists(sched_path)
    sched_status = ("LOADED" if has_sched else "FILE MISSING", "LOADED" if has_sched else "[bold yellow]FILE MISSING[/]")

    checks = [
        ("CORE PROCESSORS", cpu_status),
        ("NEURAL NETWORK", nn_status),
        ("VOICE RECOGNITION", voice_status),
        ("ACTIVE AI ENGINE", ai_status),
        ("SCHEDULE MODULE", sched_status),
    ]

    for item, (log_status, display_status) in checks:
        time.sleep(0.08)
        console.print(Align.center(f"[white]{item:25}[/] {display_status}"))

    time.sleep(0.3)
    console.print("\n")
    
    # Define overall status initialization success
    all_ok = all(stat[0] not in ("NO MIC", "OFFLINE", "KEY MISSING") for _, stat in checks)
    if all_ok:
        init_msg = "[bold cyan][ JARVIS PROTOCOLS INITIALIZED ][/bold cyan]"
        console.print(Align.center(Panel(init_msg, border_style="blue", expand=False)))
    else:
        init_msg = "[bold yellow][ JARVIS PROTOCOLS INITIALIZED WITH WARNINGS ][/bold yellow]"
        console.print(Align.center(Panel(init_msg, border_style="yellow", expand=False)))
    console.print("\n")

