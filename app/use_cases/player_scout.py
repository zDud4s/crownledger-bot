from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import resolve_clash_api_token
from domain.infra.clash_api import ClashApiClient
from domain.infra.royaleapi_scraper import get_player_war_history
from domain.models.battle import Battle
from domain.models.player import Player
from domain.scoring.war_utility_score import compute_war_utility

logger = logging.getLogger(__name__)


@dataclass
class PlayerScoutReport:
    tag: str
    name: str
    level: int
    trophies: int
    best_trophies: int
    wins: int
    losses: int
    current_clan_name: str | None
    days_since_last_any: float
    days_since_last_effective: float
    raw_7d: int
    battle_utility: float
    trend_ratio: float | None
    activity_score: float
    war_fetch_error: bool
    war_data_available: bool
    wars_analyzed: int
    wars_participated: int
    participation: float
    fame_efficiency: float
    consistency: float
    war_utility: float
    mean_fame_per_deck: float
    candidate_score: float


def _parse_battle_time(battle_time: str) -> datetime:
    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(battle_time, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.fromisoformat(battle_time.replace("Z", "+00:00"))


async def scout_player(
    player_tag: str,
    war_weeks: int = 10,
    war_history_enabled: bool = True,
) -> PlayerScoutReport:
    """
    Fetch profile, battlelog (official API) and war history (royaleapi.com scraping)
    for a single player and return a PlayerScoutReport.
    """
    token = resolve_clash_api_token()
    loop = asyncio.get_event_loop()

    def _fetch_api() -> tuple[dict, list]:
        client = ClashApiClient(token=token)
        profile = client.get_player_profile(player_tag)
        battlelog = client.get_player_battlelog(player_tag)
        return profile, battlelog

    api_task = loop.run_in_executor(None, _fetch_api)
    war_history_task = (
        get_player_war_history(player_tag)
        if war_history_enabled
        else asyncio.sleep(0, result=[])
    )
    (profile, battlelog), war_history = await asyncio.gather(api_task, war_history_task)

    clan_info = profile.get("clan") or {}
    current_clan_name = clan_info.get("name") or None

    player = Player(profile.get("tag", player_tag), profile.get("name", "?"))
    for battle in battlelog:
        battle_time = battle.get("battleTime")
        if not battle_time:
            continue
        try:
            timestamp = _parse_battle_time(battle_time)
        except ValueError:
            continue
        player.battles.append(Battle(timestamp, battle.get("type", "unknown"), raw_json=battle))

    profile_data = player.activity_profile()
    act_score = profile_data.recent_activity_score

    raw_7d = profile_data.raw_7d
    raw_14d = profile_data.raw_14d
    prev_7d = max(0, raw_14d - raw_7d)
    trend_ratio: float | None = (
        raw_7d / max(1, prev_7d) if (raw_7d > 0 or prev_7d > 0) else None
    )

    war_fetch_error = war_history is None
    safe_history: list = war_history if war_history is not None else []
    recent_history = safe_history[:war_weeks]
    wars_analyzed = len(recent_history)

    participated = [record for record in recent_history if record.decks_used > 0]
    war_records = [{"fame": record.fame, "decks_used": record.decks_used} for record in participated]
    metrics = compute_war_utility(war_records, wars_analyzed)
    war_data_available = len(participated) > 0

    if war_data_available:
        candidate_score = round(0.50 * metrics["war_utility"] + 0.50 * act_score, 2)
    else:
        candidate_score = round(act_score, 2)

    return PlayerScoutReport(
        tag=profile.get("tag", player_tag),
        name=profile.get("name", "?"),
        level=profile.get("expLevel", 0),
        trophies=profile.get("trophies", 0),
        best_trophies=profile.get("bestTrophies", 0),
        wins=profile.get("wins", 0),
        losses=profile.get("losses", 0),
        current_clan_name=current_clan_name,
        days_since_last_any=profile_data.days_since_last_any,
        days_since_last_effective=profile_data.days_since_last_effective,
        raw_7d=raw_7d,
        battle_utility=profile_data.battle_utility,
        trend_ratio=trend_ratio,
        activity_score=act_score,
        war_fetch_error=war_fetch_error,
        war_data_available=war_data_available,
        wars_analyzed=wars_analyzed,
        wars_participated=len(participated),
        participation=metrics["participation"],
        fame_efficiency=metrics["fame_efficiency"],
        consistency=metrics["consistency"],
        war_utility=metrics["war_utility"],
        mean_fame_per_deck=metrics["mean_fame_per_deck"],
        candidate_score=candidate_score,
    )
