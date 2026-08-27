"""
Per-session conversation memory that maintains message history for
multi-turn context. Each session is isolated by a unique ID.
No global or cross-session state is shared.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Maximum number of message pairs (user+assistant) to retain per session.
MAX_HISTORY_TURNS = 10


class SessionMemory:
    """
    Stores conversation history per session. Sessions are keyed by a
    unique session_id string. History is trimmed to prevent unbounded
    context growth.
    """

    def __init__(self):
        self._sessions: dict[str, list[dict[str, str]]] = {}

    # Returns the conversation history for a session, or an empty
    # list if the session does not exist yet.
    def get_history(self, session_id: str) -> list[dict[str, str]]:
        return list(self._sessions.get(session_id, []))

    # Adds a message to a session's history. Creates the session if needed.
    def add_message(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            logger.info("Created new session: %s", session_id)

        self._sessions[session_id].append({"role": role, "content": content})
        self._trim(session_id)

    # Trims the session to the last MAX_HISTORY_TURNS pairs to prevent
    # context overflow while preserving recent conversation flow.
    def _trim(self, session_id: str) -> None:
        messages = self._sessions[session_id]
        max_messages = MAX_HISTORY_TURNS * 2  # Each turn = user + assistant
        if len(messages) > max_messages:
            self._sessions[session_id] = messages[-max_messages:]

    # Clears all history for a session (used for "new conversation").
    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        logger.info("Cleared session: %s", session_id)

    # Returns True if the session exists and has messages.
    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions and len(self._sessions[session_id]) > 0
