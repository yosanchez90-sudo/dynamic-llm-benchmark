"""StarCoder2-15B accommodation (2026-07-28): its chat_template
unconditionally raise_exception()s on role="system", so
supports_system_role=False must fold SYSTEM_INSTRUCTION into the first user
turn instead, same instruction text, different delivery. Generic (no
per-model branch), controlled entirely by the caller's flag.
"""
from __future__ import annotations

from src.data.test_gen import SYSTEM_INSTRUCTION, _build_messages


def test_supports_system_role_true_sends_separate_system_message():
    messages = _build_messages("def f(): pass", "zero_shot", supports_system_role=True)
    assert messages[0] == {"role": "system", "content": SYSTEM_INSTRUCTION}
    assert messages[-1]["role"] == "user"
    assert SYSTEM_INSTRUCTION not in messages[-1]["content"]


def test_supports_system_role_false_folds_into_first_user_turn():
    messages = _build_messages("def f(): pass", "zero_shot", supports_system_role=False)
    assert all(m["role"] != "system" for m in messages)
    assert messages[0]["role"] == "user"
    assert messages[0]["content"].startswith(SYSTEM_INSTRUCTION)
    assert "def f(): pass" in messages[0]["content"]


def test_supports_system_role_false_default_is_true_unaffected():
    """Default behavior (no flag passed) must be unchanged from before this
    feature existed, regression guard against accidentally flipping the
    default for every other model."""
    messages = _build_messages("def f(): pass", "zero_shot")
    assert messages[0]["role"] == "system"
