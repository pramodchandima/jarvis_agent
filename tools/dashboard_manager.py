import os
import subprocess
import json
import time
import ssl
import re
import urllib.request
from typing import Optional
from core.ui import console
from core.browser import launch_chrome, kill_chrome_by_profile
from tools.reminder_scheduler import parse_schedule_file

from core.database import get_db_stats

# Track the spawned dashboard process
dashboard_process: Optional[subprocess.Popen] = None

# Global cache for FlightRadar24 flights
flight_cache = []
last_flight_fetch = 0.0

# Global cache for airport.lk schedule
schedule_cache = []
last_schedule_fetch = 0.0

def fetch_flightradar_flights():
    """Fetch aircraft around CMB, with ADSB.lol as a fallback for FlightRadar24."""
    global flight_cache, last_flight_fetch
    now = time.time()
    # Cache and pull once every 20 seconds
    if now - last_flight_fetch < 20:
        return flight_cache
        
    try:
        # 200 NM around CMB: North, South, West, East.  Keep this aligned with
        # gui/dashboard.js so the backend does not omit aircraft the radar can draw.
        url = "https://data-cloud.flightradar24.com/zones/fcgi/feed.js?bounds=10.52,3.85,76.52,83.25&adsb=1&air=1"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            temp_list = []
            for key, val in res_data.items():
                if key in ("full_count", "version"):
                    continue
                if isinstance(val, list) and len(val) > 13:
                    temp_list.append({
                        "icao24": val[0],
                        "callsign": (val[16] or "").strip() or "N/A",
                        "country": f"TYPE: {val[8] or 'N/A'} | REG: {val[9] or 'N/A'}",
                        "origin": val[11] or "N/A",
                        "destination": val[12] or "N/A",
                        "longitude": val[2],
                        "latitude": val[1],
                        "altitude": round(val[4] * 0.3048) if val[4] is not None else 0, # Convert feet to meters
                        "speed": round(val[5] * 1.852) if val[5] is not None else 0, # Convert knots to km/h
                        "track": val[3] or 0,
                        "emergency": "none",
                        "mach": "N/A",
                        "temp": "N/A",
                        "wind": "N/A",
                        "mcpAlt": "N/A"
                    })
            flight_cache = temp_list
            last_flight_fetch = now
    except Exception:
        pass

    # FlightRadar24's feed is undocumented and can reject requests.  Use a
    # second public ADS-B source so data.js remains useful when that happens.
    if not flight_cache:
        try:
            url = "https://api.adsb.lol/v2/lat/7.1802/lon/79.8837/dist/200"
            req = urllib.request.Request(url, headers={
                "User-Agent": "JARVIS-Dashboard/1.0",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=12) as response:
                aircraft = json.loads(response.read().decode("utf-8")).get("ac", [])

            fallback_flights = []
            for ac in aircraft:
                lat, lon = ac.get("lat"), ac.get("lon")
                if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                    continue
                if not (3.85 <= lat <= 10.52 and 76.52 <= lon <= 83.25):
                    continue

                altitude_ft = ac.get("alt_baro")
                if not isinstance(altitude_ft, (int, float)):
                    altitude_ft = ac.get("alt_geom")
                groundspeed = ac.get("gs")
                fallback_flights.append({
                    "icao24": ac.get("hex", "unknown"),
                    "callsign": (ac.get("flight") or "").strip() or "N/A",
                    "country": f"TYPE: {ac.get('t') or 'N/A'} | REG: {ac.get('r') or 'N/A'}",
                    "origin": "N/A",
                    "destination": "N/A",
                    "longitude": lon,
                    "latitude": lat,
                    "altitude": round(altitude_ft * 0.3048) if isinstance(altitude_ft, (int, float)) else 0,
                    "speed": round(groundspeed * 1.852) if isinstance(groundspeed, (int, float)) else 0,
                    "track": ac.get("track") or 0,
                    "emergency": ac.get("emergency") or "none",
                    "mach": f"{ac['mach']:.2f}" if isinstance(ac.get("mach"), (int, float)) else "N/A",
                    "temp": f"{ac['oat']}°C" if isinstance(ac.get("oat"), (int, float)) else "N/A",
                    "wind": "N/A",
                    "mcpAlt": "N/A"
                })
            if fallback_flights:
                flight_cache = fallback_flights
                last_flight_fetch = now
        except Exception:
            pass
    return flight_cache

def _clean_html(s):
    """Strip HTML tags and normalize whitespace"""
    s = re.sub(r'&#9679;', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()

def fetch_airport_schedule():
    """Scrape real arrivals+departures from airport.lk (BIA/CMB), cached for 5 minutes"""
    global schedule_cache, last_schedule_fetch
    now = time.time()
    if now - last_schedule_fetch < 300 and schedule_cache:
        return schedule_cache

    ctx = ssl._create_unverified_context()
    results = []

    for flight_type, url in [('ARR', 'https://www.airport.lk/flight_info/arrival'),
                              ('DEP', 'https://www.airport.lk/flight_info/departure')]:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req, context=ctx, timeout=12).read().decode('utf-8')

            if flight_type == 'ARR':
                fn_class = 'arr-flight-number'
                time_class = 'arr-time'
                status_class = 'arr-status'
                city_class = 'arr-city'
                rows = re.split(r'class="arr-top-row"', html)
            else:
                fn_class = 'dep-flight-number'
                time_class = 'dep-time'
                status_class = 'dep-status'
                city_class = 'dep-city'
                rows = re.split(r'class="dep-top-row"', html)

            for row in rows[1:]:
                entry = {}
                fn_match = re.search(rf'class="{fn_class}">(.*?)</div>', row, re.DOTALL)
                if not fn_match:
                    continue
                fn_raw = _clean_html(fn_match.group(1))
                parts = fn_raw.split()
                entry['callsign'] = ' '.join(parts[:2]) if len(parts) >= 2 else fn_raw

                time_match = re.search(rf'class="{time_class}">(.*?)</span>', row)
                entry['scheduled_time'] = _clean_html(time_match.group(1)) if time_match else '--:--'

                status_match = re.search(rf'class="{status_class}">(.*?)</span>', row)
                entry['status'] = _clean_html(status_match.group(1)) if status_match else 'SCHEDULED'

                city_match = re.search(rf'class="{city_class}">(.*?)</div>', row, re.DOTALL)
                entry['city'] = _clean_html(city_match.group(1)) if city_match else 'CMB'

                entry['type'] = flight_type
                results.append(entry)
        except Exception:
            pass

    if results:
        schedule_cache = results
        last_schedule_fetch = now
    return schedule_cache


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
    
    # Get FlightRadar24 flights via Python backend (CORS-proof)
    radar_flights = fetch_flightradar_flights()

    # Get real airport schedule from airport.lk
    airport_schedule = fetch_airport_schedule()

    # Build package
    data = {
        "schedule": serializable_events,
        "db_memories": mems,
        "db_conversations": convs,
        "db_skills": skills,
        "opensky_flights": radar_flights,
        "airport_schedule": airport_schedule
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
