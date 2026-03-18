from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass

from domain.infra.clash_api import ClashApiClient, encode_tag
from domain.scoring.war_utility_score import compute_war_utility


@dataclass
class WarPlayerStats:
    tag: str
    name: str
    wars_participated: int   # races where decksUsed > 0
    total_wars: int          # actual N (may be less than requested if history is short)
    participation: float     # sum(decksUsed) / (wars_participated * 20), 0.0-1.0
    fame_efficiency: float   # mean(fame/decks_used)/250, capped 0.0-1.0
    consistency: float       # wars_participated / total_wars, 0.0-1.0
    war_utility: float       # composite score, 0.0-1.0
    mean_fame_per_deck: float  # absolute value for display


def rank_players_by_war_utility(clan_tag: str, wars: int) -> list[WarPlayerStats]:
    """
    Fetch the River Race log for the clan and rank all participants by war utility.

    Args:
        clan_tag: clan tag (will be normalized)
        wars:     number of past races to analyse (clamped by caller to 1-10)

    Returns list of WarPlayerStats sorted by war_utility descending.
    """
    token = os.environ["CLASH_API_TOKEN"]
    client = ClashApiClient(token=token)

    current_members = {encode_tag(m["tag"]) for m in client.get_clan_members(clan_tag)}

    races = client.get_river_race_log(clan_tag, limit=wars)
    actual_n = min(wars, len(races))

    if actual_n == 0:
        return []

    normalized_clan_tag = encode_tag(clan_tag)

    # Collect per-player war records across all races.
    # Structure: {player_tag: {"name": str, "records": [{fame, decks_used}, ...]}}
    player_data: dict[str, dict] = defaultdict(lambda: {"name": "", "records": []})

    for race in races:
        standings = race.get("standings", [])
        clan_entry = None
        for standing in standings:
            clan = standing.get("clan", {})
            if encode_tag(clan.get("tag", "")) == normalized_clan_tag:
                clan_entry = clan
                break

        if clan_entry is None:
            continue

        for participant in clan_entry.get("participants", []):
            decks_used = participant.get("decksUsed", 0)
            if decks_used == 0:
                continue  # player did not participate in this race

            tag = participant.get("tag", "")
            if encode_tag(tag) not in current_members:
                continue  # skip players no longer in the clan
            player_data[tag]["name"] = participant.get("name", "")
            player_data[tag]["records"].append({
                "fame": participant.get("fame", 0),
                "decks_used": decks_used,
            })

    results: list[WarPlayerStats] = []
    for tag, data in player_data.items():
        records = data["records"]
        if not records:
            continue

        metrics = compute_war_utility(records, actual_n)
        results.append(WarPlayerStats(
            tag=tag,
            name=data["name"],
            wars_participated=len(records),
            total_wars=actual_n,
            participation=metrics["participation"],
            fame_efficiency=metrics["fame_efficiency"],
            consistency=metrics["consistency"],
            war_utility=metrics["war_utility"],
            mean_fame_per_deck=metrics["mean_fame_per_deck"],
        ))

    results.sort(key=lambda p: p.war_utility, reverse=True)
    return results
