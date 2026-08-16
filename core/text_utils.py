import re
from core.config_manager import config

def strip_action_tags(text: str) -> str:
    """Helper to strip internal execution tags and clean up remaining broken punctuation"""
    text = re.sub(r"\[\[UPDATE_SCHEDULE:.*?\]\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[\[PLAY_MUSIC:.*?\]\]", "", text)
    text = re.sub(r"\[\[ADD_MEMORY:.*?\]\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[\[GENERATE_SKILL:.*?\]\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[\[EXECUTE_SKILL:.*?\]\]", "", text)
    text = text.replace("[[STOP_MUSIC]]", "")
    text = text.replace("[[SHOW_DASHBOARD]]", "")
    text = text.replace("[[HIDE_DASHBOARD]]", "")
    text = text.replace("[[SHOW_SPACE_DASHBOARD]]", "")
    text = text.replace("[[HIDE_SPACE_DASHBOARD]]", "")
    
    # Fix leftover broken punctuation from tag removals (e.g. ", .", ", ,", "Sir, .")
    text = re.sub(r'\s*,\s*\.', '.', text)
    text = re.sub(r'\s*,\s*,', ',', text)
    text = re.sub(r'\s*\.\s*\.', '.', text)
    text = re.sub(r'\bSir\s*,\s*\.', 'Sir.', text)
    text = re.sub(r'\bSir\s*,\s*$', 'Sir.', text)
    text = re.sub(r'\s*,\s*$', '', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def strip_emotion_tag(text: str) -> tuple[str, str, str]:
    """
    Remove emotion tags if present and return (clean_text, pitch, rate).
    Applies pitch and rate adjustments based on config.EMOTION_MAP.
    """
    pitch, rate = "+0Hz", "+18%"
    clean_text = text.strip()
    
    for tag, (p_mod, r_mod) in getattr(config, 'EMOTION_MAP', {}).items():
        if clean_text.startswith(tag):
            clean_text = clean_text.replace(tag, "", 1).strip()
            pitch = p_mod
            rate = r_mod if r_mod != "+0%" else "+18%"
            break
            
    return clean_text, pitch, rate

def clean_display_text(text: str) -> str:
    """Helper that cleans both action tags and emotion tags for presentation"""
    cleaned = strip_action_tags(text)
    # Strip emotion tags for display
    cleaned, _, _ = strip_emotion_tag(cleaned)
    return cleaned
