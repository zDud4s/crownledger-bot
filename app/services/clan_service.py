from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.config import resolve_clash_api_token
from domain.infra.clash_api import ClashApiClient
from domain.models.battle import Battle
from domain.models.player import Player


def _parse_battle_time(battle_time: str) -> datetime:
    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(battle_time, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(battle_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Unrecognized battleTime format: {battle_time}") from exc


def fetch_players_with_battles(
    clan_tag: str,
    max_members: Optional[int] = None,
) -> List[Player]:
    """
    Fetch members + battlelog for each member and return a list of domain Players.
    Note: This is blocking I/O (requests). Call it via asyncio.to_thread inside Discord command.
    """
    client = ClashApiClient(token=resolve_clash_api_token())
    members = client.get_clan_members(clan_tag)

    if max_members is not None:
        members = members[:max_members]

    players: List[Player] = []

    for member in members:
        player = Player(member["tag"], member["name"])
        entries = client.get_player_battlelog(member["tag"])

        for battle in entries:
            battle_time = battle.get("battleTime")
            if not battle_time:
                continue

            timestamp = _parse_battle_time(battle_time)
            battle_type = battle.get("type", "unknown")
            player.battles.append(Battle(timestamp, battle_type, raw_json=battle))

        players.append(player)

    return players
