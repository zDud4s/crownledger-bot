from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from domain.models.player import Player
from domain.models.battle import Battle
from infrastructure.clash_api.client import ClashApiClient
from infrastructure.clash_api.clans import sanitize_tag


def parse_battle_time(battle_time: str) -> datetime:
    """
    Clash Royale battleTime típico:
    "YYYYMMDDTHHMMSS.000Z"
    Ex: "20231220T123456.000Z"

    Returns: timezone-aware datetime (UTC)
    """
    dt = datetime.strptime(battle_time, "%Y%m%dT%H%M%S.%fZ")
    return dt.replace(tzinfo=timezone.utc)


def fetch_players_with_battles(clan_tag: str, max_members: Optional[int] = None) -> List[Player]:
    """
    Fetch members + battlelog for each member and return a list of domain Players.
    Note: This is blocking I/O (requests). Call it via asyncio.to_thread inside Discord command.
    """
    client = ClashApiClient()

    clan_clean = sanitize_tag(clan_tag)
    members_payload = client.get(f"/clans/%23{clan_clean}/members")
    members = members_payload.get("items", [])

    if max_members is not None:
        members = members[:max_members]

    players: List[Player] = []

    for m in members:
        # m contém: tag, name, role, etc.
        p = Player(m["tag"], m["name"])

        ptag = sanitize_tag(m["tag"])
        battlelog = client.get(f"/players/%23{ptag}/battlelog")

        # battlelog é normalmente uma lista de entries
        # em alguns casos pode vir com keys; então normalizamos
        if isinstance(battlelog, dict):
            entries = battlelog.get("items", [])
        else:
            entries = battlelog

        for b in entries:
            battle_time = b.get("battleTime")
            if not battle_time:
                # muito raro, mas não vale rebentar tudo por uma entry
                continue

            ts = parse_battle_time(battle_time)
            battle_type = b.get("type", "unknown")

            # Guardamos raw_json para filtros ponderados (casual vs ranked vs challenge)
            p.battles.append(Battle(ts, battle_type, raw_json=b))

        players.append(p)

    return players
