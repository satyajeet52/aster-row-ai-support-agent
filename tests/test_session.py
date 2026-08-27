"""
Tests for the session memory module.
Validates session isolation, history tracking, and trimming.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.memory.session import SessionMemory


@pytest.fixture
def memory():
    return SessionMemory()


# Confirms that new sessions start with empty history.
def test_empty_session(memory):
    history = memory.get_history("nonexistent")
    assert history == []


# Confirms that messages are stored and retrievable.
def test_add_and_retrieve(memory):
    memory.add_message("s1", "user", "Hello")
    memory.add_message("s1", "assistant", "Hi there!")
    history = memory.get_history("s1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


# Confirms that different sessions are completely isolated.
def test_session_isolation(memory):
    memory.add_message("session-a", "user", "Question for session A")
    memory.add_message("session-b", "user", "Question for session B")

    history_a = memory.get_history("session-a")
    history_b = memory.get_history("session-b")

    assert len(history_a) == 1
    assert len(history_b) == 1
    assert "session A" in history_a[0]["content"]
    assert "session B" in history_b[0]["content"]


# Confirms that clearing a session removes its history.
def test_clear_session(memory):
    memory.add_message("s1", "user", "Hello")
    memory.clear_session("s1")
    assert memory.get_history("s1") == []


# Confirms that has_session returns False for empty/nonexistent sessions.
def test_has_session(memory):
    assert memory.has_session("s1") is False
    memory.add_message("s1", "user", "Hello")
    assert memory.has_session("s1") is True
    memory.clear_session("s1")
    assert memory.has_session("s1") is False


# Confirms that history is trimmed to max turns.
def test_trimming(memory):
    for i in range(30):
        memory.add_message("s1", "user", f"Message {i}")
        memory.add_message("s1", "assistant", f"Reply {i}")

    history = memory.get_history("s1")
    # Should be trimmed to MAX_HISTORY_TURNS * 2 = 20 messages
    assert len(history) == 20


# Confirms that get_history returns a copy, not a reference.
def test_history_is_copy(memory):
    memory.add_message("s1", "user", "Hello")
    history = memory.get_history("s1")
    history.append({"role": "user", "content": "Injected"})
    # Original should be unchanged.
    assert len(memory.get_history("s1")) == 1
