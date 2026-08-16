import os
import subprocess
import json
import time
import urllib.request
from typing import Optional
from core.ui import console
from core.browser import launch_chrome, kill_chrome_by_profile

space_dashboard_process: Optional[subprocess.Popen] = None

# Background cache variables
iss_cache = {}
astronauts_cache = {}
nasa_apod_cache = {}
solar_wind_cache = {}
earthquake_cache = {}
crypto_cache = {}
maritime_cache = {}

last_fetch_times = {
    "iss": 0.0,
    "astros": 0.0,
    "nasa": 0.0,
    "solar": 0.0,
    "earthquakes": 0.0,
    "crypto": 0.0,
    "maritime": 0.0
}

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))

def update_space_data():
    """Fetch all data and write to space_data.js"""
    global iss_cache, astronauts_cache, nasa_apod_cache, solar_wind_cache
    global earthquake_cache, crypto_cache, maritime_cache, last_fetch_times
    now = time.time()

    # 1. ISS coordinates — every 5 seconds
    if now - last_fetch_times["iss"] > 5 or not iss_cache:
        try:
            iss_cache = fetch_json("https://api.wheretheiss.at/v1/satellites/25544")
            last_fetch_times["iss"] = now
        except Exception:
            pass

    # 2. Astronauts list — every 600 seconds
    if now - last_fetch_times["astros"] > 600 or not astronauts_cache:
        try:
            astronauts_cache = fetch_json("http://api.open-notify.org/astros.json")
            last_fetch_times["astros"] = now
        except Exception:
            pass

    # 3. NASA APOD — every 3600 seconds (1 hour)
    if now - last_fetch_times["nasa"] > 3600 or not nasa_apod_cache:
        try:
            nasa_apod_cache = fetch_json("https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY")
            last_fetch_times["nasa"] = now
        except Exception:
            pass

    # 4. NOAA Space Weather — every 300 seconds
    if now - last_fetch_times["solar"] > 300 or not solar_wind_cache:
        try:
            wind = fetch_json("https://services.swpc.noaa.gov/products/summary/solar-wind-speed.json")
            scales = fetch_json("https://services.swpc.noaa.gov/products/noaa-scales.json")
            solar_wind_cache = {"wind": wind, "scales": scales}
            last_fetch_times["solar"] = now
        except Exception:
            pass

    # 5. USGS Earthquakes (M4.5+ last 24h) — every 120 seconds
    if now - last_fetch_times["earthquakes"] > 120 or not earthquake_cache:
        try:
            earthquake_cache = fetch_json(
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
            )
            last_fetch_times["earthquakes"] = now
        except Exception:
            pass

    # 6. Crypto prices (CoinGecko free API) — every 60 seconds
    if now - last_fetch_times["crypto"] > 60 or not crypto_cache:
        try:
            raw = fetch_json(
                "https://api.coingecko.com/api/v3/simple/price"
                "?ids=bitcoin,ethereum,binancecoin,solana,ripple,dogecoin"
                "&vs_currencies=usd"
            )
            crypto_cache = {
                "btc": raw.get("bitcoin", {}).get("usd"),
                "eth": raw.get("ethereum", {}).get("usd"),
                "bnb": raw.get("binancecoin", {}).get("usd"),
                "sol": raw.get("solana", {}).get("usd"),
                "xrp": raw.get("ripple", {}).get("usd"),
                "doge": raw.get("dogecoin", {}).get("usd"),
                "gold": None,   # Optional: add metals API
                "oil": None,    # Optional: add commodities API
                "lkr": None,    # Optional: add forex API
                "eur": None
            }
            last_fetch_times["crypto"] = now
        except Exception:
            pass

    # 7. Maritime status — static operational data, refresh every 1800s
    if now - last_fetch_times["maritime"] > 1800 or not maritime_cache:
        try:
            # Note: Real-time AIS requires a paid API key (MarineTraffic, VesselFinder, etc.)
            # This provides best-available public data status
            maritime_cache = {
                "vessel_count": 80000,          # Approximate global active vessels
                "piracy_zone": "GULF OF ADEN",
                "suez_status": "OPERATIONAL",
                "malacca_status": "CLEAR"
            }
            last_fetch_times["maritime"] = now
        except Exception:
            pass

    # Write combined data to space_data.js
    gui_dir = "gui"
    if not os.path.exists(gui_dir):
        os.makedirs(gui_dir)

    js_path = os.path.join(gui_dir, "space_data.js")

    data = {
        "iss": iss_cache,
        "astros": astronauts_cache,
        "nasa": nasa_apod_cache,
        "space_weather": solar_wind_cache,
        "earthquakes": earthquake_cache,
        "crypto": crypto_cache,
        "maritime": maritime_cache
    }

    try:
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(f"window.space_data = {json.dumps(data, indent=2)};")
    except Exception as e:
        console.print(f"[yellow]Warning:[/] Failed to write space dashboard data: {e}")


def show_space_dashboard():
    """Launch the space dashboard in borderless Chrome app window"""
    global space_dashboard_process

    update_space_data()

    html_path = os.path.abspath(os.path.join("gui", "space_dashboard.html"))
    if not os.path.exists(html_path):
        console.print("[bold red]Error:[/] gui/space_dashboard.html file missing.")
        return

    if space_dashboard_process:
        console.print("[bold yellow]System:[/] Space Dashboard is already open.")
        return

    file_url = f"file:///{html_path}"
    profile_dir = os.path.join(os.path.abspath("gui"), "space_profile")

    try:
        space_dashboard_process = launch_chrome(
            file_url,
            profile_name=profile_dir,
            app_mode=True,
            size="1400,820",
            position="100,60"
        )
        console.print("[bold green]System:[/] Orbital Telemetry Core HUD initiated.")
    except Exception as e:
        console.print(f"[bold red]Space Dashboard Error:[/] Failed to launch: {e}")


def hide_space_dashboard() -> bool:
    """Close the space dashboard"""
    global space_dashboard_process
    try:
        if space_dashboard_process:
            profile_dir = os.path.join(os.path.abspath("gui"), "space_profile")
            kill_chrome_by_profile(profile_dir, space_dashboard_process)
            space_dashboard_process = None
            console.print("[bold yellow]System:[/] Orbital Telemetry Core HUD closed.")
            return True
        console.print("[bold yellow]System:[/] No active space dashboard window found.")
        return False
    except Exception as e:
        console.print(f"[red]Error closing space dashboard:[/] {e}")
        return False
