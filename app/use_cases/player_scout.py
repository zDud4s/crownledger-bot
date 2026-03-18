from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from domain.infra.clash_api import ClashApiClient
from domain.infra.royaleapi_scraper import get_player_war_history
from domain.models.battle import Battle
from domain.models.player import Player
from domain.scoring.recent_activity_score import recent_activity_score
from domain.scoring.war_utility_score import compute_war_utility

logger = logging.getLogger(__name__)


@dataclass
class PlayerScoutReport:
    # Perfil
    tag: str
    name: str
    level: int
    trophies: int
    best_trophies: int
    wins: int
    losses: int
    current_clan_name: str | None

    # Atividade (battlelog)
    days_since_last_effective: float
    weighted_7d: float
    effective_7d: int
    trend_ratio: float | None
    activity_score: float          # 0.0–1.0

    # Guerras (RoyaleAPI scraping)
    war_fetch_error: bool          # True se o scraping falhou (timeout/erro)
    war_data_available: bool       # True se tiver ≥1 semana com decks_used > 0
    wars_analyzed: int             # semanas no histórico considerado
    wars_participated: int         # semanas com decks_used > 0
    participation: float           # 0.0–1.0
    fame_efficiency: float         # 0.0–1.0
    consistency: float             # 0.0–1.0
    war_utility: float             # 0.0–1.0
    mean_fame_per_deck: float

    # Score final
    candidate_score: float         # 0.0–1.0


def _parse_battle_time(battle_time: str) -> datetime:
    for fmt in ("%Y%m%dT%H%M%S.%fZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(battle_time, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.fromisoformat(battle_time.replace("Z", "+00:00"))


async def scout_player(player_tag: str, war_weeks: int = 10) -> PlayerScoutReport:
    """
    Fetch profile, battlelog (official API) and war history (royaleapi.com scraping)
    for a single player and return a PlayerScoutReport.
    """
    token = os.environ["CLASH_API_TOKEN"]
    loop = asyncio.get_event_loop()

    # Use separate clients to avoid concurrent access to the same requests.Session.
    # Profile + battlelog run sequentially in one thread; scraping runs in parallel.
    def _fetch_api() -> tuple[dict, list]:
        client = ClashApiClient(token=token)
        prof = client.get_player_profile(player_tag)
        blog = client.get_player_battlelog(player_tag)
        return prof, blog

    api_task = loop.run_in_executor(None, _fetch_api)
    war_history_task = get_player_war_history(player_tag)

    (profile, battlelog), war_history = await asyncio.gather(
        api_task, war_history_task
    )

    # --- Perfil ---
    clan_info = profile.get("clan") or {}
    current_clan_name = clan_info.get("name") or None

    # --- Atividade ---
    player = Player(profile.get("tag", player_tag), profile.get("name", "?"))
    for b in battlelog:
        bt = b.get("battleTime")
        if not bt:
            continue
        try:
            ts = _parse_battle_time(bt)
        except ValueError:
            continue
        player.battles.append(Battle(ts, b.get("type", "unknown"), raw_json=b))

    snap = player.activity_snapshot()
    act_score = recent_activity_score(snap)

    weighted_7d = float(snap.get("weighted_7d", 0.0))
    weighted_14d = float(snap.get("weighted_14d", 0.0))
    prev_7d = max(0.0, weighted_14d - weighted_7d)
    trend_ratio: float | None = (
        weighted_7d / max(0.1, prev_7d) if (weighted_7d > 0 or prev_7d > 0) else None
    )

    # --- Guerras ---
    war_fetch_error = war_history is None
    safe_history: list = war_history if war_history is not None else []

    recent_history = safe_history[:war_weeks]
    wars_analyzed = len(recent_history)

    participated = [r for r in recent_history if r.decks_used > 0]
    war_records = [{"fame": r.fame, "decks_used": r.decks_used} for r in participated]

    metrics = compute_war_utility(war_records, wars_analyzed)
    war_data_available = len(participated) > 0

    # --- Candidate score ---
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
        days_since_last_effective=snap.get("days_since_last_effective", float("inf")),
        weighted_7d=weighted_7d,
        effective_7d=int(snap.get("effective_7d", 0)),
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
