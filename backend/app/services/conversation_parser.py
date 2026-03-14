from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedMessage:
    role: str
    content: str
    position: int


def _flatten_content(content: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def extract_messages(conversation_json: dict[str, Any]) -> list[ParsedMessage]:
    messages_raw = conversation_json.get("messages", [])
    parsed: list[ParsedMessage] = []
    for idx, msg in enumerate(messages_raw):
        role = msg.get("role", "unknown")
        content = _flatten_content(msg.get("content", []))
        parsed.append(ParsedMessage(role=role, content=content, position=idx))
    return parsed


def extract_prompt(messages: list[ParsedMessage]) -> str | None:
    for msg in messages:
        if msg.role == "user" and msg.content:
            return msg.content
    return None


def extract_summary(messages: list[ParsedMessage]) -> str | None:
    user_text = None
    assistant_text = None
    for msg in messages:
        if msg.role == "user" and msg.content and user_text is None:
            user_text = msg.content
        if msg.role == "assistant" and msg.content and assistant_text is None:
            assistant_text = msg.content
        if user_text and assistant_text:
            break
    if not user_text and not assistant_text:
        return None
    parts = [part for part in [user_text, assistant_text] if part]
    return "\n".join(parts)


def estimate_tokens(messages: list[ParsedMessage]) -> int:
    word_count = sum(len(msg.content.split()) for msg in messages if msg.content)
    return max(1, int(word_count * 1.3)) if word_count else 0


def detect_language(messages: list[ParsedMessage]) -> str | None:
    if not messages:
        return None
    return "en"
