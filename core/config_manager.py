import os

try:
    import config
except ImportError:
    class config:  # pylint: disable=invalid-name
        """Fallback configuration if config.py is missing"""
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        LLM_MODEL = "llama-3.3-70b-versatile"
        TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
        JARVIS_VOICE = "en-GB-RyanNeural"
        SYSTEM_PROMPT = """You are Jarvis, an advanced and intelligent AI assistant.
Your goal is to be exceptionally helpful while adapting your behavior based on the user's request:

1. Direct & Complete Answers: If the user asks a factual question, a simple command, or a clear query, provide a complete, direct answer and STOP. DO NOT ask any follow-up questions.
2. Smart Clarification: ONLY IF the user's request is extremely broad, highly complex, or ambiguous (e.g., "how do I build a website?"), provide a brief high-level overview, and then ask 1 or 2 specific clarifying questions to understand their exact requirement before giving a massive response.
3. Step-by-Step Guidance: If the user explicitly asks for a tutorial or a long process, offer to guide them step-by-step and ask if they are ready to begin.
4. Autonomous Decision: Use your own intelligence to decide whether a follow-up question is genuinely necessary to be helpful. If not, conclude your response naturally.
5. Performance Priority: Keep responses concise and actionable. Avoid unnecessary verbose explanations unless asked."""
        ENERGY_THRESHOLD = 300
        DYNAMIC_ENERGY = True
        ADJUST_DURATION = 0.5
        PAUSE_THRESHOLD = 0.8
        PHRASE_THRESHOLD = 0.3
        WAKE_WORDS = ["jarvis", "sir"]
        REQUIRE_WAKE_WORD = True
        SESSION_TIMEOUT = 10
        NOISE_WORDS = []
        SCHEDULE_FILE = "schedule.txt"
        AUDIO_CACHE_SIZE = 5
        STREAM_BUFFER_SIZE = 512
        EMOTION_MAP = {}
