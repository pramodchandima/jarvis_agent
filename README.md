# JARVIS AI Assistant 🤖

JARVIS (Just A Rather Very Intelligent System) is a sophisticated voice-activated AI assistant inspired by the iconic J.A.R.V.I.S. from Iron Man. It combines advanced Language Models with real-time speech recognition, voice synthesis, and utility modules like schedule management and YouTube music playback.

## ✨ Features

- **🗣️ Voice Interaction**: Hands-free operation with natural speech recognition and high-quality voice synthesis.
- **🧠 Advanced Intelligence**: Powered by Groq's Llama 3 models for lightning-fast, witty, and contextual responses.
- **📅 Schedule Management**: Keep track of your daily tasks by simply talking to JARVIS. It updates a local `schedule.txt` file automatically.
- **🎵 YouTube Music Integration**: Request any song, and JARVIS will search YouTube and play it for you in the background.
- **🛡️ Intelligent Wake-Word**: Optimized to listen only when addressed as "Jarvis" or "Sir", with customizable session timeouts.
- **🎭 Emotion-Aware Responses**: JARVIS adjusts its voice pitch and rate based on its perceived "mood" (Witty, Dry, Sarcastic, etc.).

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **FFmpeg**: Required for audio processing. [Download here](https://ffmpeg.org/download.html).
- **API Keys**:
    - [Groq API Key](https://console.groq.com/)
    - [Google Cloud Console](https://console.cloud.google.com/) (YouTube Data API v3 enabled)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/jarvis-agent.git
   cd jarvis-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to a new file named `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```

4. **Initialize Schedule**:
   Ensure `schedule.txt` exists in the root directory (even if empty).

### Running JARVIS
Simply run the main script:
```bash
python main.py
```

## 🛠️ Project Structure

- `main.py`: Core logic for speech recognition, LLM interaction, and system flow.
- `config.py`: Centralized configuration for models, voice settings, and prompts.
- `youtube_utils.py`: Helper functions for searching and downloading audio from YouTube.
- `schedule.txt`: Your local persistent schedule data.
- `.env`: (Ignored by Git) Contains sensitive API credentials.

## ⚙️ Configuration

You can customize JARVIS behavior in `config.py`:
- `JARVIS_VOICE`: Change the TTS persona.
- `WAKE_WORDS`: Add or modify activation phrases.
- `REQUIRE_WAKE_WORD`: Toggle whether a wake word is needed for every command.
- `SESSION_TIMEOUT`: Set how long JARVIS stays active after the last interaction.

## 🤝 Contributing

Feel free to fork this project, submit PRs, or open issues for feature requests!

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---
*Developed with ❤️ to bring a touch of Stark Industries to your desktop.*
