from __future__ import annotations

from dataclasses import dataclass

from domain.models.player import Player
from domain.scoring.recent_activity_score import (
    recent_activity_score,
    TIER_INACTIVE_MAX,
    TIER_AT_RISK_MAX,
)


@dataclass
class PlayerHealth:
    name: str
    tag: str
    score: float
    days_since_last_any: float       # desde qualquer batalha (incluindo casual/event)
    days_since_last_effective: float  # desde última batalha ranked (peso >= 1.0)
    effective_7d: int
    trend_ratio: float | None  # rácio semana atual / semana anterior (para arrow)
    weighted_7d: float               # volume ponderado nos últimos 7 dias


@dataclass
class ClanHealthReport:
    clan_tag: str
    total_members: int
    inactive: list[PlayerHealth]   # score < TIER_INACTIVE_MAX
    at_risk: list[PlayerHealth]    # TIER_INACTIVE_MAX <= score < TIER_AT_RISK_MAX
    active: list[PlayerHealth]     # score >= TIER_AT_RISK_MAX


def compute_clan_health(clan_tag: str, players: list[Player]) -> ClanHealthReport:
    entries: list[PlayerHealth] = []

    for p in players:
        snap = p.activity_snapshot()
        score = recent_activity_score(snap)

        weighted_7d = float(snap.get("weighted_7d", 0.0))
        weighted_14d = float(snap.get("weighted_14d", 0.0))
        prev_7d = max(0.0, weighted_14d - weighted_7d)

        if weighted_7d > 0 or prev_7d > 0:
            trend_ratio = weighted_7d / max(0.1, prev_7d)
        else:
            trend_ratio = None

        entries.append(PlayerHealth(
            name=p.name,
            tag=p.tag,
            score=score,
            days_since_last_any=snap.get("days_since_last_any", float("inf")),
            days_since_last_effective=snap.get("days_since_last_effective", float("inf")),
            effective_7d=int(snap.get("effective_7d", 0)),
            trend_ratio=trend_ratio,
            weighted_7d=weighted_7d,
        ))

    # Jogadores sem qualquer batalha ranked no histórico são forçados a EM RISCO,
    # a menos que tenham um volume diário muito alto (>= 3 batalhas ponderadas/dia).
    HIGH_VOLUME_PER_DAY = 5.0

    def _no_ranked(e: PlayerHealth) -> bool:
        return not (e.days_since_last_effective < float("inf"))

    def _high_volume(e: PlayerHealth) -> bool:
        return (e.weighted_7d / 7.0) >= HIGH_VOLUME_PER_DAY

    inactive = sorted(
        [e for e in entries if e.score < TIER_INACTIVE_MAX],
        key=lambda e: e.score,
    )
    # Jogadores cujo score os poria nos ATIVOS mas sem ranked e baixo volume → EM RISCO
    at_risk = sorted(
        [e for e in entries if TIER_INACTIVE_MAX <= e.score < TIER_AT_RISK_MAX]
        + [e for e in entries if e.score >= TIER_AT_RISK_MAX and _no_ranked(e) and not _high_volume(e)],
        key=lambda e: e.score,
    )
    active = sorted(
        [e for e in entries if e.score >= TIER_AT_RISK_MAX and not (_no_ranked(e) and not _high_volume(e))],
        key=lambda e: e.score,
    )

    return ClanHealthReport(
        clan_tag=clan_tag,
        total_members=len(entries),
        inactive=inactive,
        at_risk=at_risk,
        active=active,
    )
