from __future__ import annotations

from typing import Any


def _text_from_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            parts.append(_text_from_content(item))
        return "\n".join([p for p in parts if p])
    if isinstance(content, dict):
        if "text" in content and isinstance(content["text"], str):
            return content["text"]
        if "parts" in content:
            return _text_from_content(content["parts"])
        if "content" in content:
            return _text_from_content(content["content"])
    return ""


def _canonical_message(role: str, content: str, msg_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": role,
        "content": [{"type": "text", "text": content}],
    }
    if msg_id:
        payload["id"] = msg_id
    return payload


def to_canonical(messages: list[dict[str, Any]]) -> dict[str, Any]:
    canonical: list[dict[str, Any]] = []
    for idx, msg in enumerate(messages):
        role = msg.get("role") or msg.get("author", {}).get("role") or "unknown"
        raw_content = msg.get("content") if "content" in msg else msg.get("text")
        content = _text_from_content(raw_content)
        if not content:
            continue
        msg_id = msg.get("id") or msg.get("message_id") or f"msg{idx}"
        canonical.append(_canonical_message(role, content, msg_id))
    return {"messages": canonical}


def find_message_list(obj: Any, depth: int = 0, max_depth: int = 6) -> list[dict[str, Any]] | None:
    if depth > max_depth:
        return None
    if isinstance(obj, list) and obj:
        if all(isinstance(item, dict) for item in obj):
            if any("role" in item for item in obj) and any(
                key in item for key in ("content", "text") for item in obj
            ):
                return obj
        for item in obj:
            found = find_message_list(item, depth + 1, max_depth)
            if found:
                return found
    if isinstance(obj, dict):
        for value in obj.values():
            found = find_message_list(value, depth + 1, max_depth)
            if found:
                return found
    return None


def extract_chatgpt_mapping(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    shared = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("sharedConversation")
        or payload.get("props", {}).get("pageProps", {}).get("conversation")
    )
    if not isinstance(shared, dict):
        return None
    mapping = shared.get("mapping")
    if not isinstance(mapping, dict):
        return None
    messages: list[dict[str, Any]] = []
    for node in mapping.values():
        msg = node.get("message") if isinstance(node, dict) else None
        if not isinstance(msg, dict):
            continue
        author = msg.get("author", {}) or {}
        content = msg.get("content", {}) or {}
        parts = content.get("parts") or content.get("content") or content.get("text")
        messages.append(
            {
                "id": msg.get("id"),
                "role": author.get("role") or msg.get("role"),
                "content": parts,
                "create_time": msg.get("create_time", 0),
            }
        )
    if not messages:
        return None
    messages.sort(key=lambda item: item.get("create_time", 0))
    return messages
