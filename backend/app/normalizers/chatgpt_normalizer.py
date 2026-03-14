from typing import Any


def normalize_chatgpt(raw: dict[str, Any]) -> dict[str, Any]:
    return {"messages": raw.get("messages", [])}
