import urllib.request
import urllib.parse
import json
import sqlite3
import re

def run():
    # Default fallback values (Colombo)
    city_name = "Colombo"
    lat, lon = 6.9271, 79.8612
    
    # Common Sri Lankan phonetic typos to official spelling map
    location_corrections = {
        "badulla": "Badulla",
        "badull": "Badulla",
        "badula": "Badulla",
        "kandi": "Kandy",
        "kandee": "Kandy",
        "galla": "Galle",
        "negambo": "Negombo",
        "colomb": "Colombo",
        "colomboo": "Colombo",
        "jaffnaa": "Jaffna",
        "yapahuwa": "Yapahuwa",
        "anuradapura": "Anuradhapura",
        "polonnaruwaa": "Polonnaruwa",
        "nuwara eliya": "Nuwara Eliya",
        "nuwareliya": "Nuwara Eliya",
        "hambantote": "Hambantota",
        "mataraa": "Matara",
        "trinco": "Trincomalee",
        "trinkomalee": "Trincomalee",
        "batticalo": "Batticaloa",
        "kalutare": "Kalutara"
    }
    
    try:
        # Connect to jarvis database to check the last user message
        conn = sqlite3.connect("jarvis.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM conversations WHERE role='user' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        user_msg = row[0] if row else ""
        has_specific_location = False
        
        if user_msg:
            # Strip punctuation and convert to lowercase to find location names
            cleaned = re.sub(r'[^\w\s]', '', user_msg).lower()
            
            # Check for multi-word locations first (e.g. nuwara eliya)
            search_city = None
            for typo, correction in location_corrections.items():
                if typo in cleaned:
                    search_city = correction
                    break
            
            if not search_city:
                words = cleaned.split()
                # Common non-city words to filter out
                stop_words = {
                    "what", "is", "the", "weather", "now", "today", "in", "at", "for", 
                    "jarvis", "sir", "temperature", "temp", "how", "like", "feels", "report",
                    "current", "area", "give", "me", "show", "tell", "forecast", "please", "latest"
                }
                potential_cities = [w for w in words if w not in stop_words]
                if potential_cities:
                    candidate = potential_cities[0]
                    # Apply single-word phonetic correction if matched
                    search_city = location_corrections.get(candidate, candidate.capitalize())
            
            if search_city:
                # Use Open-Meteo Geocoding API to dynamically find coordinates of the city
                # (Note: Geocoding API itself is also fuzzy and auto-corrects typos like "badula" -> "Badulla")
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(search_city)}&count=1&language=en&format=json"
                req_geo = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_geo, timeout=5) as resp:
                    geo_data = json.loads(resp.read().decode('utf-8'))
                    results = geo_data.get("results")
                    if results:
                        city_name = results[0].get("name", search_city)
                        lat = results[0].get("latitude", lat)
                        lon = results[0].get("longitude", lon)
                        has_specific_location = True

        # If no specific city is mentioned in the query, detect user location via IP-API
        if not has_specific_location:
            try:
                ip_url = "http://ip-api.com/json/"
                req_ip = urllib.request.Request(ip_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_ip, timeout=4) as resp:
                    ip_data = json.loads(resp.read().decode('utf-8'))
                    if ip_data.get("status") == "success":
                        city_name = ip_data.get("city", city_name)
                        lat = ip_data.get("lat", lat)
                        lon = ip_data.get("lon", lon)
            except Exception:
                pass # Fallback to Colombo if IP location fails
                
    except Exception:
        pass # Fallback to Colombo on general error
        
    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,surface_pressure,dew_point_2m&daily=sunrise,sunset,uv_index_max,precipitation_probability_max&timezone=auto"
        air_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=pm2_5,ozone"
        
        req_w = urllib.request.Request(weather_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_w, timeout=10) as response:
            weather_data = json.loads(response.read().decode('utf-8'))
            
        req_a = urllib.request.Request(air_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_a, timeout=10) as response:
            air_data = json.loads(response.read().decode('utf-8'))
            
        current = weather_data.get("current", {})
        air_current = air_data.get("current", {})
        
        temp = round(current.get("temperature_2m", 0))
        feels_like = round(current.get("apparent_temperature", 0))
        humidity = current.get("relative_humidity_2m", 0)
        wind_speed = current.get("wind_speed_10m", 0)
        clouds = current.get("cloud_cover", 0)
        code = current.get("weather_code", 0)
        
        pm25 = round(air_current.get("pm2_5", 0))
        
        desc = "Clear Sky"
        if code == 0: desc = "Sunny"
        elif 1 <= code <= 3: desc = "Cloudy"
        elif 45 <= code <= 48: desc = "Foggy"
        elif (51 <= code <= 67) or (80 <= code <= 82): desc = "Rainy"
        elif 95 <= code <= 99: desc = "Thunderstorm"
        
        return f"Weather in {city_name}: {desc}, Temp: {temp}°C (Feels like: {feels_like}°C), Humidity: {humidity}%, Cloud Cover: {clouds}%, Wind Speed: {wind_speed} km/h, PM2.5: {pm25} µg/m³."
    except Exception as e:
        return f"Failed to retrieve weather data for {city_name}: {e}"
