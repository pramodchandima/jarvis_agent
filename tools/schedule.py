import os
from core.config_manager import config
from core.ui import console

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
