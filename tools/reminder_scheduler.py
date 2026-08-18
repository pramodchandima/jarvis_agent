import asyncio
import os
import re
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
            content = f.read()
        
        raw_items = []
        for line in content.split("\n"):
            for part in line.split(";"):
                part = part.strip()
                if part:
                    raw_items.append(part)
        
        for item in raw_items:
            date_match = re.search(r"(\d{4})[-/.](\d{2})[-/.](\d{2})", item)
            is_yyyy_mm_dd = True
            if not date_match:
                date_match = re.search(r"(\d{2})[-/.](\d{2})[-/.](\d{4})", item)
                is_yyyy_mm_dd = False
                
            if date_match:
                if is_yyyy_mm_dd:
                    year, month, day = date_match.group(1), date_match.group(2), date_match.group(3)
                else:
                    day, month, year = date_match.group(1), date_match.group(2), date_match.group(4) if len(date_match.groups()) >= 4 else date_match.group(3)
                
                # Check for 12-hour format time match, e.g. "9:00 AM" or "10:30 PM"
                time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)", item, re.IGNORECASE)
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2)) if time_match.group(2) else 0
                    meridiem = time_match.group(3).upper()
                    if meridiem == "PM" and hours < 12:
                        hours += 12
                    elif meridiem == "AM" and hours == 12:
                        hours = 0
                    time_str = f"{hours:02d}:{minutes:02d}"
                else:
                    # 24-hour format: "HH:MM"
                    time_24_match = re.search(r"(\d{2}):(\d{2})", item)
                    if time_24_match:
                        time_str = time_24_match.group(0)
                    else:
                        time_str = "00:00"
                
                try:
                    event_dt = datetime.strptime(f"{year}-{month}-{day} {time_str}", "%Y-%m-%d %H:%M")
                    
                    # Clean text
                    clean_text = item
                    # Remove date string
                    clean_text = clean_text.replace(date_match.group(0), "")
                    # Remove weekday name
                    clean_text = re.sub(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", "", clean_text, flags=re.IGNORECASE)
                    # Remove empty parentheses/brackets
                    clean_text = re.sub(r"\(\s*\)|\[\s*\]", "", clean_text)
                    
                    # Remove time range or time match
                    clean_text = re.sub(r"\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*-\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)", "", clean_text, flags=re.IGNORECASE)
                    if time_match:
                        clean_text = clean_text.replace(time_match.group(0), "")
                    
                    # Remove multiple commas/dashes/spaces
                    clean_text = re.sub(r",\s*,", ",", clean_text)
                    clean_text = clean_text.strip(" ,-")
                    
                    if not clean_text:
                        clean_text = item
                        
                    events.append({
                        "datetime": event_dt,
                        "text": clean_text,
                        "original_line": item
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
