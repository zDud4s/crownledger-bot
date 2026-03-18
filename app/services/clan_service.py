from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

from domain.models.player import Player
from domain.models.battle import Battle
from domain.infra.clash_api import ClashApiClient


def _parse_battle_time(battle_time: str) -> datetime:
    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(battle_time, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(battle_time.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"Formato de battleTime não reconhecido: {battle_time}") from e


def fetch_players_with_battles(clan_tag: str, max_members: Optional[int] = None) -> List[Player]:
    """
    Fetch members + battlelog for each member and return a list of domain Players.
    Note: This is blocking I/O (requests). Call it via asyncio.to_thread inside Discord command.
    """
    token = os.getenv("CLASH_API_TOKEN")
    if not token:
        raise RuntimeError("CLASH_API_TOKEN não está definido no ambiente (.env).")

    client = ClashApiClient(token=token)

    members = client.get_clan_members(clan_tag)

    if max_members is not None:
        members = members[:max_members]

    players: List[Player] = []

    for m in members:
        p = Player(m["tag"], m["name"])

        entries = client.get_player_battlelog(m["tag"])

        for b in entries:
            battle_time = b.get("battleTime")
            if not battle_time:
                continue

            ts = _parse_battle_time(battle_time)
            battle_type = b.get("type", "unknown")
            p.battles.append(Battle(ts, battle_type, raw_json=b))

        players.append(p)

    return players
