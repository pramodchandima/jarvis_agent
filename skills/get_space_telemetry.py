import urllib.request
import json

def run():
    try:
        req_iss = urllib.request.Request("https://api.wheretheiss.at/v1/satellites/25544", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_iss, timeout=10) as r:
            iss = json.loads(r.read().decode('utf-8'))
            
        req_ast = urllib.request.Request("http://api.open-notify.org/astros.json", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_ast, timeout=10) as r:
            ast = json.loads(r.read().decode('utf-8'))
            
        iss_lat = round(iss.get("latitude", 0), 4)
        iss_lon = round(iss.get("longitude", 0), 4)
        iss_vel = round(iss.get("velocity", 0))
        iss_alt = round(iss.get("altitude", 0))
        
        num_astros = ast.get("number", 0)
        astros_names = [p.get("name") for p in ast.get("people", [])]
        astros_list = ", ".join(astros_names)
        
        return f"ISS Telemetry: Latitude: {iss_lat}, Longitude: {iss_lon}, Velocity: {iss_vel} km/h, Altitude: {iss_alt} km. There are currently {num_astros} astronauts in space: {astros_list}."
    except Exception as e:
        return f"Failed to retrieve space telemetry: {e}"
