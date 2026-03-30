from __future__ import annotations

from dataclasses import dataclass

from domain.models.player import Player
from domain.scoring.recent_activity_score import (
    TIER_INACTIVE_MAX,
    TIER_AT_RISK_MAX,
)


@dataclass
class PlayerHealth:
    name: str
    tag: str
    score: float
    days_since_last_any: float
    days_since_last_effective: float
    raw_7d: int
    trend_ratio: float | None
    battle_utility: float


@dataclass
class ClanHealthReport:
    clan_tag: str
    total_members: int
    inactive: list[PlayerHealth]
    at_risk: list[PlayerHealth]
    active: list[PlayerHealth]


def compute_clan_health(clan_tag: str, players: list[Player]) -> ClanHealthReport:
    entries: list[PlayerHealth] = []

    for p in players:
        prof = p.activity_profile()
        score = prof.recent_activity_score

        raw_7d = prof.raw_7d
        raw_14d = prof.raw_14d
        prev_7d = max(0, raw_14d - raw_7d)

        if raw_7d > 0 or prev_7d > 0:
            trend_ratio = raw_7d / max(1, prev_7d)
        else:
            trend_ratio = None

        entries.append(PlayerHealth(
            name=p.name,
            tag=p.tag,
            score=score,
            days_since_last_any=prof.days_since_last_any,
            days_since_last_effective=prof.days_since_last_effective,
            raw_7d=raw_7d,
            trend_ratio=trend_ratio,
            battle_utility=prof.battle_utility,
        ))

    inactive = sorted(
        [e for e in entries if e.score < TIER_INACTIVE_MAX],
        key=lambda e: e.score,
    )
    at_risk = sorted(
        [e for e in entries if TIER_INACTIVE_MAX <= e.score < TIER_AT_RISK_MAX],
        key=lambda e: e.score,
    )
    active = sorted(
        [e for e in entries if e.score >= TIER_AT_RISK_MAX],
        key=lambda e: e.score,
    )

    return ClanHealthReport(
        clan_tag=clan_tag,
        total_members=len(entries),
        inactive=inactive,
        at_risk=at_risk,
        active=active,
    )
