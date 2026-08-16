import os
import subprocess
import webbrowser
import json
import time
import urllib.request
from datetime import datetime
from typing import Optional
from core.ui import console
from core.browser import launch_chrome, kill_chrome_by_profile
from tools.reminder_scheduler import parse_schedule_file

from core.database import get_db_stats

# Track the spawned dashboard process
dashboard_process: Optional[subprocess.Popen] = None

# Global cache for OpenSky flights to bypass browser CORS limits and respect API rate limits
opensky_cache = []
last_opensky_fetch = 0.0

def fetch_opensky_flights():
    """Fetch OpenSky flights using Python standard library (no CORS limits)"""
    global opensky_cache, last_opensky_fetch
    now = time.time()
    # Cache and pull once every 60 seconds to avoid 429 rate limits
    if now - last_opensky_fetch < 60:
        return opensky_cache
        
    try:
        url = "https://opensky-network.org/api/states/all?lamin=3.5&lamax=12.3&lomin=76.3&lomax=85.1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            states = res_data.get("states")
            if states:
                temp_list = []
                for s in states:
                    icao24 = s[0]
                    callsign = (s[1] or "").strip() or "N/A"
                    lon = s[5]
                    lat = s[6]
                    if lon is None or lat is None:
                        continue
                    temp_list.append({
                        "icao24": icao24,
                        "callsign": callsign,
                        "country": f"ORIG: {s[2] or 'N/A'}",
                        "longitude": lon,
                        "latitude": lat,
                        "altitude": round(s[7] or 0),
                        "speed": round((s[9] or 0) * 3.6), # Convert m/s to km/h
                        "track": s[10] or 0,
                        # Defaults for OpenSky state limits
                        "emergency": "none",
                        "mach": "N/A",
                        "temp": "N/A",
                        "wind": "N/A",
                        "mcpAlt": "N/A"
                    })
                opensky_cache = temp_list
                last_opensky_fetch = now
    except Exception:
        # Silently fail and use previous cached list on temporary errors/rate limits
        pass
    return opensky_cache

def update_dashboard_data():
    """Build and write the current schedule and system variables to data.js"""
    gui_dir = "gui"
    if not os.path.exists(gui_dir):
        os.makedirs(gui_dir)
        
    js_path = os.path.join(gui_dir, "data.js")
    
    # Get schedule events
    events = parse_schedule_file()
    serializable_events = []
    for ev in events:
        serializable_events.append({
            "datetime": ev["datetime"].strftime("%Y-%m-%d %H:%M"),
            "text": ev["text"]
        })
        
    # Get database metrics
    mems, convs, skills = get_db_stats()
    
    # Get OpenSky flights via Python backend (CORS-proof)
    opensky_flights = fetch_opensky_flights()
    
    # Build package
    data = {
        "schedule": serializable_events,
        "db_memories": mems,
        "db_conversations": convs,
        "db_skills": skills,
        "opensky_flights": opensky_flights
    }
    
    try:
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(f"window.jarvis_data = {json.dumps(data, indent=2)};")
    except Exception as e:
        console.print(f"[yellow]Warning:[/] Failed to write dashboard data: {e}")

def show_dashboard():
    """Launch the dashboard in a borderless Chrome app window on the right side of the screen"""
    global dashboard_process
    
    # Update data once before launching
    update_dashboard_data()
    
    html_path = os.path.abspath(os.path.join("gui", "dashboard.html"))
    if not os.path.exists(html_path):
        console.print("[bold red]Error:[/] gui/dashboard.html file missing.")
        return
        
    if dashboard_process:
        console.print("[bold yellow]System:[/] Dashboard is already open.")
        return
        
    file_url = f"file:///{html_path}"
    
    try:
        profile_dir = os.path.join(os.path.abspath("gui"), "dashboard_profile")
        dashboard_process = launch_chrome(
            file_url,
            profile_name=profile_dir,
            app_mode=True,
            size="1000,720",
            position="200,100"
        )
        console.print("[bold green]System:[/] Glowing Sidebar Dashboard initiated.")
    except Exception as e:
        console.print(f"[bold red]Dashboard Error:[/] Failed to launch: {e}")

def hide_dashboard() -> bool:
    """Close the dashboard by terminating its process tree"""
    global dashboard_process
    try:
        profile_dir = os.path.join(os.path.abspath("gui"), "dashboard_profile")
        kill_chrome_by_profile(profile_dir, dashboard_process)
        dashboard_process = None
        console.print("[bold yellow]System:[/] Glowing Sidebar Dashboard closed.")
        return True
    except Exception as e:
        console.print(f"[red]Error closing dashboard:[/] {e}")
        return False
