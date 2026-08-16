import re
from typing import Tuple
from core.types import RequestComplexity

def analyze_request_complexity(user_input: str) -> Tuple[RequestComplexity, bool]:
    """
    Intelligently analyze if user needs clarification questions.
    Returns (complexity_level, requires_clarification)
    """
    lower_input = user_input.lower().strip()
    
    # Simple direct questions/commands - NO clarification needed
    simple_patterns = [
        r'^(what|when|where|who|how)\s+(\w+\s+)?(is|are|was|were)',  # Direct questions
        r'^(tell|show|play|stop|pause|resume)',  # Direct commands
        r'^(yes|no|ok|okay|sure|alright)',  # Simple confirmations
        r'^(open|close|start|end)',  # Direct actions
    ]
    
    for pattern in simple_patterns:
        if re.match(pattern, lower_input):
            return RequestComplexity.SIMPLE, False
    
    # Tutorial/step-by-step requests
    tutorial_patterns = [
        r'(how do i|how to|teach me|tutorial|guide|step by step)',
        r'(walk me through|show me how)',
    ]
    
    for pattern in tutorial_patterns:
        if re.search(pattern, lower_input):
            return RequestComplexity.TUTORIAL, False
    
    # Extremely broad/ambiguous requests - CLARIFICATION needed
    ambiguous_patterns = [
        r'^(help|what|how|what\'s)',  # Very vague starts
        r'(everything about|all about|anything about)',  # Broad scope
        r'(not sure|confused|unclear)',  # User is uncertain
    ]
    
    for pattern in ambiguous_patterns:
        if re.search(pattern, lower_input):
            # Check if it's actually complex
            word_count = len(lower_input.split())
            if word_count < 4:  # Too vague
                return RequestComplexity.CLARIFICATION, True
    
    # Multi-part or conditional requests
    if any(kw in lower_input for kw in ['either', 'both', 'or', 'and', 'but']):
        if len(lower_input.split()) > 15:  # Complex multi-part
            return RequestComplexity.AMBIGUOUS, True
    
    # Default: no clarification needed
    return RequestComplexity.SIMPLE, False
