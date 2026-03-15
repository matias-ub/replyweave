from typing import Any

from app.normalizers.utils import extract_chatgpt_mapping, find_message_list, to_canonical


def normalize_chatgpt(raw: dict[str, Any]) -> dict[str, Any]:
    payload = raw.get("payload", raw)
    messages = extract_chatgpt_mapping(payload)
    if not messages:
        messages = find_message_list(payload)
    if not messages:
        return {"messages": []}
    return to_canonical(messages)
