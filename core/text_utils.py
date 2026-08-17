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

def extract_actual_response(text: str) -> str:
    """Extracts only the portion of text starting from the first emotion tag, if any."""
    tags = ["[Dry]", "[Sarcastic]", "[Concerned]", "[Witty]", "[Neutral]"]
    
    # Find the earliest occurrence of any emotion tag
    earliest_idx = -1
    for tag in tags:
        idx = text.find(tag)
        if idx != -1:
            if earliest_idx == -1 or idx < earliest_idx:
                earliest_idx = idx
                
    if earliest_idx != -1:
        return text[earliest_idx:]
    
    # If no tag is found yet, check if it contains drafting/thinking keywords.
    # If so, suppress the output (return empty string) until the actual response starts.
    lower_text = text.lower()
    drafting_keywords = ["draft:", "draft 1:", "draft 2:", "emotion:", "refining:", "checks:", "final check:", "thought:", "reasoning:"]
    if any(kw in lower_text for kw in drafting_keywords):
        return ""
        
    return text

def strip_emotion_tag(text: str) -> tuple[str, str, str]:
    """
    Remove emotion tags if present and return (clean_text, pitch, rate).
    Applies pitch and rate adjustments based on config.EMOTION_MAP.
    """
    pitch, rate = "+0Hz", "+18%"
    text = extract_actual_response(text)
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
    cleaned = extract_actual_response(text)
    cleaned = strip_action_tags(cleaned)
    # Strip emotion tags for display
    cleaned, _, _ = strip_emotion_tag(cleaned)
    return cleaned

