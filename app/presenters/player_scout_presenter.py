from __future__ import annotations

import math
from dataclasses import dataclass

from app.use_cases.player_scout import PlayerScoutReport


@dataclass(frozen=True)
class PlayerScoutViewModel:
    title_text: str
    player_tag: str
    clan_text: str
    profile_text: str
    activity_text: str
    utility_text: str
    wars_text: str
    candidate_text: str


def _score_tier(score: float) -> str:
    if score >= 0.75:
        return "Strong"
    if score >= 0.50:
        return "Solid"
    return "Low"


def _utility_label(score: float) -> str:
    if score >= 0.85:
        return "Mostly ranked, war or challenge modes."
    if score >= 0.65:
        return "Good quality battle mix."
    if score >= 0.45:
        return "Balanced mix of modes."
    if score >= 0.20:
        return "Mostly casual or event modes."
    return "Almost entirely casual or friendly modes."


def _candidate_label(score: float) -> str:
    if score >= 0.75:
        return "Excellent candidate"
    if score >= 0.55:
        return "Good option"
    if score >= 0.35:
        return "Consider"
    return "Not recommended"


def _trend_label(ratio: float | None) -> str:
    if ratio is None:
        return "No trend"
    if ratio >= 1.2:
        return "Rising"
    if ratio < 0.8:
        return "Falling"
    return "Stable"


def _days_label(days: float) -> str:
    if not math.isfinite(float(days)):
        return "never"
    if days < 0.05:
        return "today"
    if int(days) == 1:
        return "1 day"
    return f"{int(days)} days"


def present_player_scout(report: PlayerScoutReport) -> PlayerScoutViewModel:
    total_games = report.wins + report.losses
    win_rate = int(report.wins / max(total_games, 1) * 100)

    profile_text = (
        f"Level: {report.level}\n"
        f"Trophies: {report.trophies:,}\n"
        f"Best trophies: {report.best_trophies:,}\n"
        f"Wins/Losses: {report.wins:,}/{report.losses:,} ({win_rate}% win rate)"
    )

    activity_text = (
        f"Recent activity: {report.activity_score:.2f} ({_score_tier(report.activity_score)})\n"
        f"Last battle: {_days_label(report.days_since_last_any)}\n"
        f"Battles in last 7d: {report.raw_7d}\n"
        f"Trend: {_trend_label(report.trend_ratio)}"
    )

    utility_text = (
        f"Mode utility: {report.battle_utility:.2f} ({_score_tier(report.battle_utility)})\n"
        f"Last ranked battle: {_days_label(report.days_since_last_effective)}\n"
        f"{_utility_label(report.battle_utility)}"
    )

    if report.war_data_available:
        wars_text = (
            f"War utility: {report.war_utility:.2f} ({_score_tier(report.war_utility)})\n"
            f"Wars: {report.wars_participated}/{report.wars_analyzed}\n"
            f"Participation: {int(report.participation * 100)}%\n"
            f"Consistency: {int(report.consistency * 100)}%\n"
            f"Fame per deck: {int(report.mean_fame_per_deck)}"
        )
    elif report.war_fetch_error:
        wars_text = "War history unavailable due to scraping or timeout failure."
    else:
        wars_text = "No war history available for this player."

    candidate_text = (
        f"Candidate score: {report.candidate_score:.2f}\n"
        f"Assessment: {_candidate_label(report.candidate_score)}"
    )

    return PlayerScoutViewModel(
        title_text=f"{report.name} | {report.tag}",
        player_tag=report.tag,
        clan_text=report.current_clan_name or "No current clan",
        profile_text=profile_text,
        activity_text=activity_text,
        utility_text=utility_text,
        wars_text=wars_text,
        candidate_text=candidate_text,
    )
