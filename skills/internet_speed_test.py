import os
import platform
def run():
    ping_cmd = 'ping -c 1 1.1.1.1' if platform.system().lower() != 'windows' else 'ping -n 1 1.1.1.1'
    try:
        output = os.popen(ping_cmd).read()
        lines = output.splitlines()
        for line in lines:
            if 'time=' in line:
                latency = float(line.split('time=')[1].split('ms')[0])
                return f"Latency: {round(latency, 2)} ms"
    except Exception as e:
        return f"An error occurred: {str(e)}"