from datetime import datetime, timezone

_RED_PHASES = {"operator", "error"}
_COLOR_ORDER = {"red": 0, "yellow": 1, "green": 2}


def calculate_color(phase: str, updated_at: str, yellow_threshold_minutes: int) -> str:
    if phase in _RED_PHASES:
        return "red"
    if calculate_elapsed_minutes(updated_at) >= yellow_threshold_minutes:
        return "yellow"
    return "green"


def calculate_elapsed_minutes(updated_at: str) -> int:
    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    return int((datetime.now(timezone.utc) - dt).total_seconds() / 60)


def process_chats(raw_chats: list, yellow_threshold_minutes: int) -> dict:
    processed = []
    for chat in raw_chats:
        if chat["phase"] == "completed":
            continue
        color = calculate_color(chat["phase"], chat["updated_at"], yellow_threshold_minutes)
        processed.append({
            "phone_number": chat["phone_number"],
            "phase": chat["phase"],
            "color": color,
            "elapsed_minutes": calculate_elapsed_minutes(chat["updated_at"]),
            "collected": chat.get("collected", {}),
        })
    processed.sort(key=lambda c: _COLOR_ORDER[c["color"]])
    return {"chats": processed, "kpis": _build_kpis(processed)}


def _build_kpis(chats: list) -> dict:
    return {
        "total": len(chats),
        "in_progress": sum(1 for c in chats if c["color"] == "green"),
        "attention": sum(1 for c in chats if c["color"] == "yellow"),
        "action_required": sum(1 for c in chats if c["color"] == "red"),
    }
