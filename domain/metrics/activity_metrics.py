from datetime import datetime, timedelta, timezone
from domain.filters.battle_filter import battle_weight


def days_since_last_any_battle(battles):
    """
    Última batalha de qualquer tipo (inclui casual).
    Se não houver batalhas, devolve inf.
    """
    if not battles:
        return float("inf")

    now = datetime.now(timezone.utc)
    last = max(b.timestamp for b in battles)
    return (now - last).total_seconds() / 86400


def days_since_last_effective_battle(battles):
    """
    Última batalha que tenha peso > 0.
    Se só existirem batalhas com peso 0, devolve inf.
    """
    now = datetime.now(timezone.utc)

    effective_times = [
        b.timestamp for b in battles
        if battle_weight(b.raw_json) > 0.0
    ]
    if not effective_times:
        return float("inf")

    last = max(effective_times)
    return (now - last).total_seconds() / 86400


def battles_in_last_days(battles, days):
    """
    Conta batalhas (raw) nos últimos N dias.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return sum(1 for b in battles if b.timestamp >= cutoff)


def effective_battles_in_last_days(battles, days):
    """
    Conta batalhas com peso > 0 nos últimos N dias.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return sum(
        1 for b in battles
        if b.timestamp >= cutoff and battle_weight(b.raw_json) > 0.0
    )


def weighted_battles_in_last_days(battles, days: int) -> float:
    """
    Soma dos pesos das batalhas nos últimos N dias.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    total = 0.0
    for b in battles:
        if b.timestamp >= cutoff:
            total += battle_weight(b.raw_json)
    return total
