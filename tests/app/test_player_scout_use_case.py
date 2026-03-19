from __future__ import annotations

import asyncio

from app.use_cases.player_scout import scout_player


class _FakeClashApiClient:
    def __init__(self, token: str):
        self.token = token

    def get_player_profile(self, player_tag: str) -> dict:
        return {
            "tag": player_tag,
            "name": "Player One",
            "expLevel": 15,
            "trophies": 9000,
            "bestTrophies": 9100,
            "wins": 100,
            "losses": 50,
            "clan": {"name": "Clan X"},
        }

    def get_player_battlelog(self, player_tag: str) -> list[dict]:
        return []


def test_scout_player_skips_war_history_when_disabled(monkeypatch):
    state = {"called": False}

    async def fake_get_player_war_history(player_tag: str):
        state["called"] = True
        return []

    monkeypatch.setattr("app.use_cases.player_scout.resolve_clash_api_token", lambda: "token")
    monkeypatch.setattr("app.use_cases.player_scout.ClashApiClient", _FakeClashApiClient)
    monkeypatch.setattr("app.use_cases.player_scout.get_player_war_history", fake_get_player_war_history)

    report = asyncio.run(scout_player("#P1", war_weeks=10, war_history_enabled=False))

    assert state["called"] is False
    assert report.war_fetch_error is False
    assert report.war_data_available is False
    assert report.wars_analyzed == 0
