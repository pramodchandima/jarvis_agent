import asyncio
import os
import re
import time
from datetime import datetime
from core.config_manager import config
from core.ui import console
from audio.tts import speak_jarvis

# Track announced items to avoid repeats in the same session
announced_events = set()

def parse_schedule_file() -> list:
    """Parse schedule.txt and return a list of parsed events"""
    file_path = getattr(config, 'SCHEDULE_FILE', "schedule.txt")
    events = []
    if not os.path.exists(file_path):
        return events

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Simple parsing: check for YYYY-MM-DD and HH:MM if present
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", line)
            time_match = re.search(r"(\d{2}:\d{2})", line)
            
            if date_match:
                date_str = date_match.group(1)
                time_str = time_match.group(1) if time_match else "00:00"
                
                try:
                    event_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    # Extract the event text (everything after the colon or date)
                    event_text = line
                    if ":" in line:
                        event_text = line.split(":", 1)[1].strip()
                    
                    events.append({
                        "datetime": event_dt,
                        "text": event_text,
                        "original_line": line
                    })
                except ValueError:
                    pass
    except Exception as e:
        console.print(f"[yellow]Warning:[/] Error parsing schedule for reminders: {e}")
        
    return events

async def start_reminder_scheduler():
    """Background task loop that checks for upcoming schedule reminders"""
    console.print("[bold green]System:[/] Proactive Reminder Scheduler initialized.")
    while True:
        try:
            now = datetime.now()
            events = parse_schedule_file()
            
            for event in events:
                event_dt = event["datetime"]
                # Calculate time difference in seconds
                diff_seconds = (event_dt - now).total_seconds()
                
                # If event is upcoming within 10 minutes (600 seconds) and not yet announced
                if 0 <= diff_seconds <= 600 and event["original_line"] not in announced_events:
                    minutes_left = int(diff_seconds // 60)
                    announcement = f"Excuse me sir. You have an upcoming event: '{event['text']}' in about {minutes_left} minutes."
                    if minutes_left == 0:
                        announcement = f"Excuse me sir. Your event: '{event['text']}' is starting now."
                        
                    console.print(f"\n[bold yellow]Jarvis Reminder:[/] {event['text']}")
                    asyncio.create_task(speak_jarvis(announcement))
                    announced_events.add(event["original_line"])
            
            # Check every 60 seconds
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as e:
            console.print(f"[red]Reminder Scheduler Error:[/] {e}")
            await asyncio.sleep(60)
