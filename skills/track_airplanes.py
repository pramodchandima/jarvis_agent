import urllib.request
import urllib.parse
import json
import sqlite3
import re

def run():
    # Default bounding box for Sri Lanka (N, S, W, E)
    # lat: 5.9 to 9.9, lon: 79.5 to 82.0
    lamin, lamax = 5.9, 9.9
    lomin, lomax = 79.5, 82.0
    location_name = "Sri Lanka"
    
    try:
        # Connect to jarvis database to check the last user message
        conn = sqlite3.connect("jarvis.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM conversations WHERE role='user' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        user_msg = row[0] if row else ""
        search_location = None
        
        if user_msg:
            cleaned = re.sub(r'[^\w\s]', '', user_msg).lower()
            words = cleaned.split()
            
            # Words to filter out
            stop_words = {
                "what", "is", "the", "how", "many", "airplanes", "airplane", "flights", 
                "flight", "planes", "plane", "in", "at", "for", "jarvis", "sir", "track", 
                "show", "list", "are", "there", "my", "area", "current", "currently", "above"
            }
            
            potential_locations = [w for w in words if w not in stop_words]
            if potential_locations:
                search_location = " ".join(potential_locations)
                
        if search_location:
            # Call Geocoding API to find coordinates
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(search_location)}&count=1&language=en&format=json"
            req_geo = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_geo, timeout=5) as resp:
                geo_data = json.loads(resp.read().decode('utf-8'))
                results = geo_data.get("results")
                if results:
                    location_name = results[0].get("name", search_location.capitalize())
                    lat = results[0].get("latitude")
                    lon = results[0].get("longitude")
                    if lat is not None and lon is not None:
                        # Bounding box (approx 1.5 degrees)
                        lamin, lamax = lat - 1.5, lat + 1.5
                        lomin, lomax = lon - 1.5, lon + 1.5
    except Exception:
        pass # Fallback to default Sri Lanka bounds on any error

    center_lat, center_lon = (lamin + lamax) / 2.0, (lomin + lomax) / 2.0

    flight_details = []

    # 1. Primary Source: FlightRadar24 (data-cloud endpoint)
    try:
        bounds_str = f"{lamax:.2f},{lamin:.2f},{lomin:.2f},{lomax:.2f}"
        url = f"https://data-cloud.flightradar24.com/zones/fcgi/feed.js?bounds={bounds_str}&adsb=1&air=1"
        
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        })
        
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            for key, val in res_data.items():
                if key in ("full_count", "version"):
                    continue
                if isinstance(val, list) and len(val) > 13:
                    callsign = (val[16] or "").strip() or "N/A"
                    origin = val[11] or "Unknown"
                    destination = val[12] or "Unknown"
                    aircraft_type = val[8] or "Unknown"
                    altitude = f"{val[4]} ft" if val[4] is not None else "N/A"
                    speed = f"{val[5]} kts" if val[5] is not None else "N/A"
                    flight_details.append(f"• Flight {callsign} ({aircraft_type}) from {origin} to {destination}: Alt: {altitude}, Speed: {speed}")
    except Exception:
        pass

    # 2. Secondary Fallback Source: ADS-B.lol API (matching Dashboard Manager)
    if not flight_details:
        try:
            url = f"https://api.adsb.lol/v2/lat/{center_lat:.4f}/lon/{center_lon:.4f}/dist/200"
            req = urllib.request.Request(url, headers={
                "User-Agent": "JARVIS-Agent/1.0",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
                aircraft = data.get("ac", [])
                
                for ac in aircraft:
                    lat, lon = ac.get("lat"), ac.get("lon")
                    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                        continue
                    if not (lamin <= lat <= lamax and lomin <= lon <= lomax):
                        continue
                        
                    callsign = (ac.get("flight") or "").strip() or "N/A"
                    ac_type = ac.get("t") or "Unknown"
                    alt_ft = ac.get("alt_baro")
                    if not isinstance(alt_ft, (int, float)):
                        alt_ft = ac.get("alt_geom") or "N/A"
                    else:
                        alt_ft = f"{alt_ft} ft"
                    speed_kts = ac.get("gs")
                    speed_str = f"{speed_kts} kts" if isinstance(speed_kts, (int, float)) else "N/A"
                    
                    flight_details.append(f"• Flight {callsign} ({ac_type}): Alt: {alt_ft}, Speed: {speed_str}")
        except Exception:
            pass

    total_count = len(flight_details)
    if total_count == 0:
        return f"Currently, there are no active airplanes detected in {location_name}."

    summary = f"Found {total_count} active airplane(s) in {location_name}."
    if flight_details:
        summary += "\n" + "\n".join(flight_details[:15]) # Display top 15
    return summary
