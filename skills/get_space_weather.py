import urllib.request
import json

def run():
    try:
        req_w = urllib.request.Request("https://services.swpc.noaa.gov/products/summary/solar-wind-speed.json", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_w, timeout=10) as response:
            wind = json.loads(response.read().decode('utf-8'))
            
        req_s = urllib.request.Request("https://services.swpc.noaa.gov/products/noaa-scales.json", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_s, timeout=10) as response:
            scales = json.loads(response.read().decode('utf-8'))
            
        wind_speed = wind[0].get("windspd", "Unknown") if isinstance(wind, list) and wind else "Unknown"
        geomagnetic_alert = scales.get("G", {}).get("alert", "None") if isinstance(scales, dict) else "None"
        solar_radiation = scales.get("S", {}).get("alert", "None") if isinstance(scales, dict) else "None"
        radio_blackout = scales.get("R", {}).get("alert", "None") if isinstance(scales, dict) else "None"
        
        return f"Space Weather: Solar Wind Speed: {wind_speed} km/s. NOAA Alert Scales - Geomagnetic (G): {geomagnetic_alert}, Solar Radiation (S): {solar_radiation}, Radio Blackout (R): {radio_blackout}."
    except Exception as e:
        return f"Failed to retrieve space weather data: {e}"
