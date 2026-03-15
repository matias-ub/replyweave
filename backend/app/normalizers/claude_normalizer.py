from typing import Any

from app.normalizers.utils import find_message_list, to_canonical


def normalize_claude(raw: dict[str, Any]) -> dict[str, Any]:
    payload = raw.get("payload", raw)
    if isinstance(payload, dict) and isinstance(payload.get("chat_messages"), list):
        messages = payload.get("chat_messages", [])
        return to_canonical(messages)
    messages = find_message_list(payload)
    if not messages:
        return {"messages": []}
    return to_canonical(messages)
