# domain/ml/dataset.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Protocol, Any

import pandas as pd

from domain.ml.features import compute_activity_features, to_dict
from domain.ml.labels import will_be_inactive_next_days


class BattleLike(Protocol):
    timestamp: datetime
    raw_json: dict[str, Any]


class PlayerLike(Protocol):
    tag: str
    name: str
    battles: list[BattleLike]


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _min_timestamp(battles: list[BattleLike]) -> datetime | None:
    if not battles:
        return None
    ts = [_ensure_utc(b.timestamp) for b in battles]
    return min(ts) if ts else None


def _max_timestamp(battles: list[BattleLike]) -> datetime | None:
    if not battles:
        return None
    ts = [_ensure_utc(b.timestamp) for b in battles]
    return max(ts) if ts else None


@dataclass(frozen=True)
class DatasetConfig:
    horizon_days: int = 7
    snapshot_step_days: int = 1
    min_history_days: int = 14  # só cria snapshots depois de ter pelo menos isto de histórico


def build_inactivity_dataset(players: Iterable[PlayerLike], cfg: DatasetConfig) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for p in players:
        battles = list(p.battles)
        if len(battles) < 5:
            continue

        t_min = _min_timestamp(battles)
        t_max = _max_timestamp(battles)
        if t_min is None or t_max is None:
            continue

        # só criamos snapshots que permitem ver o futuro (label) dentro do histórico
        end_time = min(t_max, now) - timedelta(days=cfg.horizon_days)
        start_time = t_min + timedelta(days=cfg.min_history_days)

        if start_time >= end_time:
            continue

        t = start_time
        step = timedelta(days=cfg.snapshot_step_days)

        while t <= end_time:
            feats = compute_activity_features(battles, ref_time=t)
            x = to_dict(feats)
            y = will_be_inactive_next_days(battles, snapshot_time=t, horizon_days=cfg.horizon_days)

            row = {
                "player_tag": p.tag,
                "player_name": p.name,
                "snapshot_time": t.isoformat(),
                "y_inactive_next_7d": int(y),
                **x,
            }
            rows.append(row)
            t += step

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # sane defaults
    df.replace([float("inf")], 9999.0, inplace=True)
    df.fillna(0.0, inplace=True)

    return df
