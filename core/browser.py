import os
import subprocess
import webbrowser
import tempfile
from typing import Optional
from core.ui import console

def find_chrome_path() -> Optional[str]:
    """Search for the Google Chrome executable path on Windows"""
    paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Google\\Chrome\\Application\\chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Google\\Chrome\\Application\\chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", "C:\\Users\\Default\\AppData\\Local"), "Google\\Chrome\\Application\\chrome.exe")
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def launch_chrome(url: str, profile_name: str, app_mode: bool = False, size: str = "", position: str = "") -> subprocess.Popen:
    """Launch Chrome in isolated mode with user profile"""
    chrome_path = find_chrome_path()
    if not chrome_path:
        # Fallback to default browser
        webbrowser.open(url)
        console.print(f"[bold green]System:[/] Fallback: Opened in default browser: [italic]{url}[/]")
        # Return a dummy process-like object
        class DummyProcess:
            pid = 0
            def terminate(self):
                pass
        return DummyProcess()

    # Use a absolute profile directory or system temp directory
    if os.path.isabs(profile_name):
        profile_dir = profile_name
    else:
        profile_dir = os.path.join(tempfile.gettempdir(), profile_name)
    
    args = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    
    if app_mode:
        args.append(f"--app={url}")
        args.append("--allow-file-access-from-files")
        args.append("--disable-web-security")
    else:
        args.append("--new-window")
        args.append("--autoplay-policy=no-user-gesture-required")
        args.append(url)
        
    if size:
        args.append(f"--window-size={size}")
    if position:
        args.append(f"--window-position={position}")
        
    process = subprocess.Popen(args)
    return process

def kill_chrome_by_profile(profile_name: str, process: Optional[subprocess.Popen] = None) -> None:
    """Force close any Chrome process running with the specific profile name in command line"""
    try:
        # Stop process tree using PowerShell
        cmd = f'powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name = \'chrome.exe\' AND CommandLine LIKE \'%{profile_name}%\'\\" | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"'
        subprocess.run(cmd, shell=True, capture_output=True)
        
        if process:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
            except Exception:
                pass
    except Exception as e:
        console.print(f"[red]Error closing Chrome process for profile {profile_name}:[/] {e}")
