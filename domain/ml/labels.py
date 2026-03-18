# domain/ml/labels.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Protocol, Any

from domain.filters.battle_filter import battle_weight


class BattleLike(Protocol):
    timestamp: datetime
    raw_json: dict[str, Any]


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def will_be_inactive_next_days(
    battles: Iterable[BattleLike],
    snapshot_time: datetime,
    horizon_days: int = 7,
) -> int:
    """
    Label:
      1 => NÃO existe nenhuma batalha efetiva no intervalo (snapshot_time, snapshot_time + horizon_days]
      0 => existe pelo menos 1 batalha efetiva no intervalo
    """
    t0 = _ensure_utc(snapshot_time)
    t1 = t0 + timedelta(days=horizon_days)

    for b in battles:
        ts = _ensure_utc(b.timestamp)
        if t0 < ts <= t1:
            try:
                if battle_weight(b.raw_json) > 0.0:
                    return 0
            except Exception:
                continue
    return 1
