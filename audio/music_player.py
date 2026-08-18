import asyncio
import subprocess
from typing import Optional
from core.ui import console
from audio.tts import speak_jarvis
from tools import youtube_utils

current_music_process: Optional[subprocess.Popen] = None

from core.browser import find_chrome_path, launch_chrome, kill_chrome_by_profile


async def play_music_task(query: str) -> None:
    """Search YouTube and play the video directly in a Chrome Guest tab (non-blocking)"""
    global current_music_process  # pylint: disable=global-statement,invalid-name
    
    try:
        console.print(f"[bold cyan]System:[/] Searching for: [italic]{query}[/]")

        video_id, title = youtube_utils.search_youtube(query)
        if not video_id:
            await speak_jarvis(f"Sir, I couldn't find {query} on YouTube.")
            return

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        console.print(f"[bold cyan]System:[/] Launching browser for: [italic]{title}[/]")

        # Close any previous spawned music browser process
        if current_music_process:
            try:
                current_music_process.terminate()
            except Exception:
                pass
            current_music_process = None

        current_music_process = launch_chrome(video_url, "jarvis_chrome_profile")
        console.print(f"[bold green]System:[/] Spawning browser for: [italic]{title}[/]")

    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[bold red]Music Error:[/] {e}")
        await speak_jarvis("Sir, I'm unable to launch the browser.")

def stop_music() -> bool:
    """Stop current music playback by terminating the Chrome process tree"""
    global current_music_process
    try:
        kill_chrome_by_profile("jarvis_chrome_profile", current_music_process)
        current_music_process = None
        console.print("[bold yellow]System:[/] Music browser closed.")
        return True
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Error closing browser:[/] {e}")
        return False
