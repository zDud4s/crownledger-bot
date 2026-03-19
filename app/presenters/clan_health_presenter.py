from __future__ import annotations

import math
from dataclasses import dataclass

from app.use_cases.clan_health import ClanHealthReport, PlayerHealth
from domain.scoring.recent_activity_score import TIER_AT_RISK_MAX, TIER_INACTIVE_MAX, trend_arrow


@dataclass(frozen=True)
class ClanHealthRowViewModel:
    tier_key: str
    tier_label: str
    tier_badge: str
    name: str
    tag: str
    score_text: str
    utility_text: str
    days_since_last_any_text: str
    raw_7d_text: str
    trend_text: str


@dataclass(frozen=True)
class ClanHealthViewModel:
    clan_tag: str
    total_members: int
    inactive_count: int
    at_risk_count: int
    active_count: int
    summary_text: str
    rows: list[ClanHealthRowViewModel]


def _tier_meta(score: float) -> tuple[str, str, str]:
    if score < TIER_INACTIVE_MAX:
        return "inactive", "Inactive", "RED"
    if score < TIER_AT_RISK_MAX:
        return "at_risk", "At Risk", "YELLOW"
    return "active", "Active", "GREEN"


def _format_days(days: float) -> str:
    if not math.isfinite(float(days)):
        return "Never"
    if days < 0.05:
        return "Today"
    return f"{days:.1f}d"


def _present_player(player: PlayerHealth) -> ClanHealthRowViewModel:
    tier_key, tier_label, tier_badge = _tier_meta(player.score)
    return ClanHealthRowViewModel(
        tier_key=tier_key,
        tier_label=tier_label,
        tier_badge=tier_badge,
        name=player.name,
        tag=player.tag,
        score_text=f"{player.score:.2f}",
        utility_text=f"{player.battle_utility:.2f}",
        days_since_last_any_text=_format_days(player.days_since_last_any),
        raw_7d_text=str(player.raw_7d),
        trend_text=trend_arrow(player.trend_ratio),
    )


def present_clan_health(report: ClanHealthReport, show_active: bool) -> ClanHealthViewModel:
    rows = [
        _present_player(player)
        for player in [*report.inactive, *report.at_risk, *([*report.active] if show_active else [])]
    ]

    summary_text = (
        f"Clan {report.clan_tag} | Members: {report.total_members} | "
        f"Inactive: {len(report.inactive)} | "
        f"At Risk: {len(report.at_risk)} | "
        f"Active: {len(report.active)}"
    )

    return ClanHealthViewModel(
        clan_tag=report.clan_tag,
        total_members=report.total_members,
        inactive_count=len(report.inactive),
        at_risk_count=len(report.at_risk),
        active_count=len(report.active),
        summary_text=summary_text,
        rows=rows,
    )
