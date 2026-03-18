# domain/ml/features.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Protocol, Any

from domain.filters.battle_filter import battle_weight


class BattleLike(Protocol):
    timestamp: datetime
    raw_json: dict[str, Any]


@dataclass(frozen=True)
class ActivityFeatures:
    days_since_last_effective: float
    weighted_7d: float
    weighted_14d: float
    weighted_30d: float
    effective_7d: int
    effective_14d: int
    effective_30d: int
    active_days_7d: int
    active_days_14d: int
    active_days_30d: int
    trend_weighted_7d_vs_prev7d: float
    consistency_30d: float  # 0..1 (mais alto = mais consistente)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _effective_battles(battles: Iterable[BattleLike]) -> list[BattleLike]:
    out: list[BattleLike] = []
    for b in battles:
        try:
            if battle_weight(b.raw_json) > 0.0:
                out.append(b)
        except Exception:
            continue
    return out


def _battles_before(battles: Iterable[BattleLike], ref_time: datetime) -> list[BattleLike]:
    rt = _ensure_utc(ref_time)
    out: list[BattleLike] = []
    for b in battles:
        ts = _ensure_utc(b.timestamp)
        if ts <= rt:
            out.append(b)
    return out


def _count_effective_in_window(battles: list[BattleLike], ref_time: datetime, days: int) -> int:
    rt = _ensure_utc(ref_time)
    cutoff = rt - timedelta(days=days)
    total = 0
    for b in battles:
        ts = _ensure_utc(b.timestamp)
        if ts >= cutoff and battle_weight(b.raw_json) > 0.0:
            total += 1
    return total


def _sum_weighted_in_window(battles: list[BattleLike], ref_time: datetime, days: int) -> float:
    rt = _ensure_utc(ref_time)
    cutoff = rt - timedelta(days=days)
    total = 0.0
    for b in battles:
        ts = _ensure_utc(b.timestamp)
        if ts >= cutoff:
            try:
                total += float(battle_weight(b.raw_json))
            except Exception:
                continue
    return total


def _active_days_in_window(battles: list[BattleLike], ref_time: datetime, days: int) -> int:
    rt = _ensure_utc(ref_time)
    cutoff = rt - timedelta(days=days)
    days_set = set()
    for b in battles:
        ts = _ensure_utc(b.timestamp)
        if ts >= cutoff:
            days_set.add(ts.date())
    return len(days_set)


def _days_since_last_effective(battles: list[BattleLike], ref_time: datetime) -> float:
    rt = _ensure_utc(ref_time)
    eff = []
    for b in battles:
        try:
            if battle_weight(b.raw_json) > 0.0:
                eff.append(_ensure_utc(b.timestamp))
        except Exception:
            continue
    if not eff:
        return float("inf")
    last = max(eff)
    return (rt - last).total_seconds() / 86400.0


def _trend_weighted_7d(battles: list[BattleLike], ref_time: datetime) -> float:
    rt = _ensure_utc(ref_time)
    w_last = _sum_weighted_in_window(battles, rt, 7)
    w_prev = _sum_weighted_in_window(battles, rt - timedelta(days=7), 7)
    denom = max(1e-6, w_prev)
    return (w_last - w_prev) / denom


def _consistency_30d(battles: list[BattleLike], ref_time: datetime) -> float:
    """
    Consistência simples baseada em presença diária:
    - 30d é dividido em 4 blocos ~7d
    - mede variação da contagem de dias ativos por bloco
    Retorna 0..1 (1 = muito consistente).
    """
    rt = _ensure_utc(ref_time)
    battles_30 = []
    cutoff = rt - timedelta(days=30)
    for b in battles:
        ts = _ensure_utc(b.timestamp)
        if ts >= cutoff:
            battles_30.append(b)

    counts = []
    for k in range(4):
        end = rt - timedelta(days=7 * k)
        start = end - timedelta(days=7)
        days_set = set()
        for b in battles_30:
            ts = _ensure_utc(b.timestamp)
            if start <= ts <= end:
                days_set.add(ts.date())
        counts.append(len(days_set))

    mean = sum(counts) / len(counts)
    var = sum((c - mean) ** 2 for c in counts) / len(counts)
    # var alta => menos consistente
    return 1.0 / (1.0 + var)


def compute_activity_features(battles: Iterable[BattleLike], ref_time: datetime | None = None) -> ActivityFeatures:
    rt = _ensure_utc(ref_time or datetime.now(timezone.utc))
    before = _battles_before(battles, rt)

    weighted_7d = _sum_weighted_in_window(before, rt, 7)
    weighted_14d = _sum_weighted_in_window(before, rt, 14)
    weighted_30d = _sum_weighted_in_window(before, rt, 30)

    effective_7d = _count_effective_in_window(before, rt, 7)
    effective_14d = _count_effective_in_window(before, rt, 14)
    effective_30d = _count_effective_in_window(before, rt, 30)

    active_days_7d = _active_days_in_window(before, rt, 7)
    active_days_14d = _active_days_in_window(before, rt, 14)
    active_days_30d = _active_days_in_window(before, rt, 30)

    return ActivityFeatures(
        days_since_last_effective=_days_since_last_effective(before, rt),
        weighted_7d=weighted_7d,
        weighted_14d=weighted_14d,
        weighted_30d=weighted_30d,
        effective_7d=effective_7d,
        effective_14d=effective_14d,
        effective_30d=effective_30d,
        active_days_7d=active_days_7d,
        active_days_14d=active_days_14d,
        active_days_30d=active_days_30d,
        trend_weighted_7d_vs_prev7d=_trend_weighted_7d(before, rt),
        consistency_30d=_consistency_30d(before, rt),
    )


def to_dict(f: ActivityFeatures) -> dict[str, float]:
    # Label-friendly (só números)
    return {
        "days_since_last_effective": float(f.days_since_last_effective),
        "weighted_7d": float(f.weighted_7d),
        "weighted_14d": float(f.weighted_14d),
        "weighted_30d": float(f.weighted_30d),
        "effective_7d": float(f.effective_7d),
        "effective_14d": float(f.effective_14d),
        "effective_30d": float(f.effective_30d),
        "active_days_7d": float(f.active_days_7d),
        "active_days_14d": float(f.active_days_14d),
        "active_days_30d": float(f.active_days_30d),
        "trend_weighted_7d_vs_prev7d": float(f.trend_weighted_7d_vs_prev7d),
        "consistency_30d": float(f.consistency_30d),
    }
