from __future__ import annotations


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(int(value), maximum))


def normalize_clash_tag(tag: str) -> str:
    if tag is None:
        raise ValueError("Tag is required.")

    normalized = tag.strip().upper()
    if not normalized:
        raise ValueError("Tag is required.")

    if not normalized.startswith("#"):
        normalized = f"#{normalized}"

    return normalized


def normalize_clan_tag(tag: str) -> str:
    return normalize_clash_tag(tag)


def normalize_player_tag(tag: str) -> str:
    return normalize_clash_tag(tag)
