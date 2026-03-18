from datetime import datetime, timedelta, timezone
from domain.filters.battle_filter import battle_weight, should_ignore_battle

def battle_raw(b):
    return b.raw_json if hasattr(b, "raw_json") else b

def filter_battles(battles):
    # remove boatBattle (e futuros ignores) para TUDO
    return [b for b in battles if not should_ignore_battle(battle_raw(b))]


def _parse_battle_time(s: str) -> datetime:
    s = (s or "").strip()
    # Clash Royale costuma usar "YYYYMMDDThhmmss.SSSZ"
    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    # fallback: ISO (se algum dia vier assim)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"Unrecognized battleTime format: {s}") from e

def battle_timestamp(b) -> datetime:
    """Devolve datetime UTC da batalha (quer b seja Battle, quer seja dict)."""
    if hasattr(b, "timestamp"):
        return b.timestamp

    # dict path
    if isinstance(b, dict):
        t = b.get("timestamp")
        if isinstance(t, datetime):
            return t if t.tzinfo else t.replace(tzinfo=timezone.utc)

        bt = b.get("battleTime") or b.get("battle_time") or b.get("time")
        return _parse_battle_time(bt)

    raise TypeError(f"Unsupported battle type: {type(b)}")

def days_since_last_any_battle(battles):
    battles = filter_battles(battles)
    if not battles:
        return float("inf")
    now = datetime.now(timezone.utc)
    last = max(battle_timestamp(b) for b in battles)
    return (now - last).total_seconds() / 86400


def days_since_last_effective_battle(battles):
    """
    Última batalha ranked (peso >= 1.0).
    Se só existirem batalhas casuais, devolve inf.
    """
    battles = filter_battles(battles)
    if not battles:
        return float("inf")

    now = datetime.now(timezone.utc)

    effective_times = [
        battle_timestamp(b) for b in battles
        if battle_weight(battle_raw(b)) >= 1.0
    ]
    if not effective_times:
        return float("inf")

    last = max(effective_times)
    return (now - last).total_seconds() / 86400


def battles_in_last_days(battles, days: int) -> int:
    battles = filter_battles(battles)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    return sum(1 for b in battles if battle_timestamp(b) >= cutoff)


def effective_battles_in_last_days(battles, days: int) -> int:
    battles = filter_battles(battles)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    return sum(
        1 for b in battles
        if battle_timestamp(b) >= cutoff and battle_weight(battle_raw(b)) >= 1.0
    )


def weighted_battles_in_last_days(battles, days: int) -> float:
    battles = filter_battles(battles)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    total = 0.0
    for b in battles:
        if battle_timestamp(b) >= cutoff:
            total += battle_weight(battle_raw(b))
    return total


def days_since_oldest_battle(battles):
    battles = filter_battles(battles)
    if not battles:
        return float("inf")
    now = datetime.now(timezone.utc)
    oldest = min(battle_timestamp(b) for b in battles)
    return (now - oldest).total_seconds() / 86400


def effective_battles_total(battles):
    battles = filter_battles(battles)
    return sum(1 for b in battles if battle_weight(battle_raw(b)) >= 1.0)
