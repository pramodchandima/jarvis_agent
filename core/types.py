from enum import Enum

class RequestComplexity(Enum):
    """Request complexity classification"""
    SIMPLE = 1  # Direct answer needed
    CLARIFICATION = 2  # Needs follow-up questions
    TUTORIAL = 3  # Step-by-step guidance
    AMBIGUOUS = 4  # Unclear intent
