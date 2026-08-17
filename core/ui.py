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

    # 4. GROQ CLOUD LINK
    try:
        socket.setdefaulttimeout(1.2)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("api.groq.com", 443))
        network_ok = True
    except Exception:
        network_ok = False
    link_status = ("CONNECTED" if network_ok else "OFFLINE", "CONNECTED" if network_ok else "[bold red]OFFLINE[/]")

    # 5. SMART ANALYSIS ENGINE
    has_key = bool(config.GROQ_API_KEY)
    engine_status = ("LOADED" if has_key else "KEY MISSING", "LOADED" if has_key else "[bold red]KEY MISSING[/]")

    # 6. SCHEDULE MODULE
    sched_path = getattr(config, 'SCHEDULE_FILE', "schedule.txt")
    has_sched = os.path.exists(sched_path)
    sched_status = ("LOADED" if has_sched else "FILE MISSING", "LOADED" if has_sched else "[bold yellow]FILE MISSING[/]")

    checks = [
        ("CORE PROCESSORS", cpu_status),
        ("NEURAL NETWORK", nn_status),
        ("VOICE RECOGNITION", voice_status),
        ("GROQ CLOUD LINK", link_status),
        ("SMART ANALYSIS ENGINE", engine_status),
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

