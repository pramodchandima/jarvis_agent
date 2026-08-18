<div align="center">

<h1>⚙️ J.A.R.V.I.S. AI Agent</h1>
<p><em>Just A Rather Very Intelligent System — Brought to your Desktop</em></p>

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA3-F55036?style=for-the-badge&logo=lightning&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)

<br/>

> A sophisticated, voice-activated AI assistant inspired by the iconic J.A.R.V.I.S. from Iron Man.  
> Combines a real-time HUD dashboard, LLM intelligence, speech I/O, and live global data feeds.

</div>

---

## ✨ Feature Highlights

| Module | Description |
|--------|-------------|
| 🗣️ **Voice I/O** | Hands-free operation — speak naturally, get synthesised British-accent responses |
| 🧠 **LLM Intelligence** | Powered by Groq's LLaMA 3 for fast, witty, context-aware replies |
| 🎭 **Emotion Engine** | Adjusts voice tone (pitch/rate) based on mood tags: `[Witty]`, `[Sarcastic]`, `[Dry]`… |
| 📅 **Schedule Manager** | Talk to add/remove tasks — auto-updates `schedule.txt` |
| 🎵 **YouTube Music** | Say *"Play something by Hans Zimmer"* — JARVIS finds & streams it |
| 🛡️ **Wake Word** | Listens passively, activates only on "Jarvis" / "Sir" |
| 🧠 **Memory & Recall** | SQLite-backed conversation memory with session reflections |
| 🖥️ **HUD Dashboard** | Dual-dashboard cyberpunk interface (see below) |

---

## 🖥️ HUD Dashboards

### 🌐 AI Cognitive Network Dashboard
Live Jarvis status with airspace radar, weather data, and system telemetry.
<p align="center">
  <img src="assets/AI%20COGNITIVE%20NETWORK.png" alt="AI Cognitive Network Dashboard" width="800">
</p>

### 🛰️ Orbital Telemetry Core
A real-time global intelligence HUD featuring:
<p align="center">
  <img src="assets/ORBITAL%20TELEMETRY%20CORE.png" alt="Orbital Telemetry Core Dashboard" width="800">
</p>

| Panel | Data Source | Refresh |
|-------|-------------|---------|
| 🛰️ ISS Live Orbital Map | wheretheiss.at | 5s |
| 👨‍🚀 Orbital Crew Registry | open-notify.org | 10 min |
| ☀️ NOAA Space Weather | swpc.noaa.gov | 5 min |
| 🌋 USGS Earthquake Feed (M4.5+) | earthquake.usgs.gov | 2 min |
| 🔭 NASA Astronomy Picture | api.nasa.gov | Hourly |
| 💰 Crypto Ticker (BTC/ETH/SOL…) | CoinGecko API | 60s |
| 🚢 Maritime Status Core | Static / configurable | — |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **FFmpeg** — for audio processing → [Download](https://ffmpeg.org/download.html)
- **Google Chrome** — for the HUD dashboards
- **API Keys:**
  - [Groq API Key](https://console.groq.com/) — LLM inference (free tier available)
  - [Google API Key](https://console.cloud.google.com/) — YouTube Data API v3 (for music)

### Installation

```bash
# 1. Clone
git clone https://github.com/pramodchandima/jarvis-agent.git
cd jarvis-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
copy .env.example .env
# Then edit .env with your API keys

# 4. Run
python main.py
```

### `.env` Configuration

```env
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# Optional overrides:
# LLM_MODEL=llama-3.3-70b-versatile
# TRANSCRIPTION_MODEL=whisper-large-v3-turbo
```

---

## 🗂️ Project Structure

```
jarvis-agent/
│
├── main.py                    # Entry point — voice loop, orchestration
├── config.py                  # All settings, prompts, emotion maps
├── requirements.txt
│
├── ai/
│   ├── llm.py                 # LLM response generation & tool parsing
│   └── intent_analyzer.py     # Request complexity scoring
│
├── audio/
│   ├── tts.py                 # Edge-TTS voice synthesis
│   ├── stt.py                 # Whisper speech-to-text
│   ├── music_player.py        # YouTube audio playback (pygame)
│   └── microphone.py          # Mic calibration utilities
│
├── core/
│   ├── database.py            # SQLite memory & conversation logs
│   ├── browser.py             # Chrome launcher helpers
│   ├── config_manager.py      # Runtime config loader
│   ├── text_utils.py          # Text cleaning & helpers
│   ├── types.py               # Shared type definitions
│   └── ui.py                  # Rich console rendering
│
├── tools/
│   ├── dashboard_manager.py       # AI Cognitive Network HUD
│   ├── space_dashboard_manager.py # Orbital Telemetry Core HUD
│   ├── reminder_scheduler.py      # Background reminder engine
│   ├── schedule.py                # Schedule file read/write
│   ├── skill_manager.py           # Dynamic skill loader
│   └── youtube_utils.py           # YT search & download
│
├── gui/
│   ├── dashboard.html/css/js       # AI Cognitive Network dashboard
│   ├── space_dashboard.html/css/js # Orbital Telemetry Core dashboard
│   └── data.json                   # Shared config for GUI (auto-generated)
│
└── skills/                    # Pluggable skill scripts
```

---

## ⚙️ Configuration (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `JARVIS_VOICE` | `en-GB-RyanNeural` | Edge-TTS voice persona |
| `WAKE_WORDS` | `["jarvis", "sir"]` | Activation phrases |
| `REQUIRE_WAKE_WORD` | `True` | Toggle always-on listening |
| `SESSION_TIMEOUT` | `12` | Seconds of silence before session ends |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Groq model selection |
| `ENERGY_THRESHOLD` | `1000` | Microphone noise sensitivity |

---

## 💬 Voice Command Examples

```
"Jarvis, what's on my schedule today?"
"Play something calm by Hans Zimmer"
"Add a reminder to call John at 3 PM"
"Open the satellite dashboard"
"Stop the music"
"What's the ISS altitude right now?"
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

1. Fork the repo
2. Create your feature branch: `git checkout -b feat/my-feature`
3. Commit: `git commit -m 'feat: add my feature'`
4. Push: `git push origin feat/my-feature`
5. Open a Pull Request

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
<sub>Developed with ❤️ — Bringing a touch of Stark Industries to your desktop.</sub>
</div>
