from __future__ import annotations

from dataclasses import dataclass

from app.use_cases.war_rank import WarPlayerStats


@dataclass(frozen=True)
class WarRankRowViewModel:
    rank_text: str
    tier_label: str
    name: str
    tag: str
    utility_text: str
    wars_text: str
    participation_text: str
    consistency_text: str
    fame_text: str


@dataclass(frozen=True)
class WarRankViewModel:
    clan_tag: str
    requested_wars: int
    actual_wars: int
    total_players: int
    summary_text: str
    rows: list[WarRankRowViewModel]


def _score_tier(score: float) -> str:
    if score >= 0.75:
        return "Strong"
    if score >= 0.50:
        return "Solid"
    return "Low"


def present_war_rank(
    clan_tag: str,
    requested_wars: int,
    players: list[WarPlayerStats],
) -> WarRankViewModel:
    actual_wars = players[0].total_wars if players else 0
    rows = [
        WarRankRowViewModel(
            rank_text=str(index),
            tier_label=_score_tier(player.war_utility),
            name=player.name or "?",
            tag=player.tag,
            utility_text=f"{player.war_utility:.2f}",
            wars_text=f"{player.wars_participated}/{player.total_wars}",
            participation_text=f"{int(player.participation * 100)}%",
            consistency_text=f"{int(player.consistency * 100)}%",
            fame_text=str(int(player.mean_fame_per_deck)),
        )
        for index, player in enumerate(players, start=1)
    ]

    summary_text = (
        f"Clan {clan_tag} | Players: {len(players)} | "
        f"Wars requested: {requested_wars} | "
        f"Wars used: {actual_wars}"
    )

    return WarRankViewModel(
        clan_tag=clan_tag,
        requested_wars=requested_wars,
        actual_wars=actual_wars,
        total_players=len(players),
        summary_text=summary_text,
        rows=rows,
    )
