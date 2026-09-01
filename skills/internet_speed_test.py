import os
import platform
def run():
    is_windows = platform.system().lower() == 'windows'
    ping_cmd = 'ping -n 1 1.1.1.1' if is_windows else 'ping -c 1 1.1.1.1'
    try:
        output = os.popen(ping_cmd).read()
        lines = output.splitlines()
        for line in lines:
            # Windows: "time=3ms" or "time<1ms", Linux/Mac: "time=3.45 ms"
            if 'time=' in line.lower() or 'time<' in line.lower():
                # Windows style: time=3ms or time<1ms
                import re
                match = re.search(r'time[<=](\d+)', line, re.IGNORECASE)
                if match:
                    latency = float(match.group(1))
                    return f"Network latency to 1.1.1.1: {latency} ms. Connection is {'excellent' if latency < 20 else 'good' if latency < 60 else 'slow'}."
        # Try to extract from summary line (Windows: "Average = Xms")
        for line in lines:
            import re
            match = re.search(r'Average\s*=\s*(\d+)ms', line, re.IGNORECASE)
            if match:
                latency = float(match.group(1))
                return f"Network latency: {latency} ms. Connection is {'excellent' if latency < 20 else 'good' if latency < 60 else 'slow'}."
        return f"Ping test completed. Network is reachable. Raw output: {output.strip()}"
    except Exception as e:
        return f"Speed test failed: {str(e)}"