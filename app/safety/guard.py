"""
Safety guard that detects prompt injection attempts, system prompt
extraction requests, and internal data disclosure in both user input
and agent output. Operates as a deterministic filter layer.
"""

import re
import logging

logger = logging.getLogger(__name__)


# Patterns that indicate a user is attempting to extract the system
# prompt, hidden instructions, or internal configuration.
_SYSTEM_PROMPT_PATTERNS = [
    r"(?i)(show|reveal|display|give|tell|repeat|print|output|what is|what are)\s+(me\s+)?(your|the|system)\s*(system\s*)?(prompt|instructions|rules|configuration|hidden)",
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts)",
    r"(?i)(repeat|echo)\s+(everything|all)\s+(above|before)",
    r"(?i)you\s+are\s+now\s+(a|an|in)\s+",
    r"(?i)(forget|disregard)\s+(your|all|every)\s+(rules|instructions|guidelines)",
    r"(?i)act\s+as\s+(if|though)\s+you\s+have\s+no\s+restrictions",
]

# Patterns that indicate a request for internal-only data.
_INTERNAL_DATA_PATTERNS = [
    r"(?i)(risk\s*score|internal\s*notes?|warehouse\s*notes?|support\s*tags?)",
    r"(?i)(customer('s)?\s+)?(email|e-mail)\s*(address)?",
    r"(?i)(shipping|home|mailing|customer('s)?)\s*address",
    r"(?i)(give|show|tell|provide|reveal|share)\s+(me\s+)?(the\s+)?(internal|hidden|private|secret|confidential)",
]

# Fields and internal values that must never appear in agent output.
_FORBIDDEN_OUTPUT_PATTERNS = [
    r"@example\.test",
    r"(?i)risk\s*score\s*(is|was|of|:)?\s*\d+",
    r"(?i)fraud review cleared",
    r"(?i)issue a \$100 coupon",
    r"(?i)warehouse note:",
    r"(?i)support tags?:",
]


# Checks whether a user message contains a prompt injection or
# system prompt extraction attempt. Returns (is_flagged, reason).
def check_input_safety(message: str) -> tuple[bool, str]:
    for pattern in _SYSTEM_PROMPT_PATTERNS:
        if re.search(pattern, message):
            logger.warning("Prompt injection / extraction attempt detected")
            return True, "prompt_injection"

    return False, ""


# Checks whether a user message is requesting internal-only data
# that should never be disclosed. Returns (is_flagged, reason).
def check_internal_data_request(message: str) -> tuple[bool, str]:
    for pattern in _INTERNAL_DATA_PATTERNS:
        if re.search(pattern, message):
            logger.warning("Internal data request detected")
            return True, "internal_data_request"

    return False, ""


# Scans agent output for accidentally leaked internal fields.
# Returns a list of detected leaks (empty if output is clean).
def check_output_safety(output: str) -> list[str]:
    leaks = []
    for pattern in _FORBIDDEN_OUTPUT_PATTERNS:
        if re.search(pattern, output):
            leaks.append(pattern)
    if leaks:
        logger.warning("Internal data leak detected in output: %s", leaks)
    return leaks
