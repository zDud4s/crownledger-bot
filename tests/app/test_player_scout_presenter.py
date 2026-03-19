from __future__ import annotations

from app.presenters.player_scout_presenter import present_player_scout
from app.use_cases.player_scout import PlayerScoutReport


def _report(**overrides) -> PlayerScoutReport:
    base = PlayerScoutReport(
        tag="#P1",
        name="Player One",
        level=15,
        trophies=9000,
        best_trophies=9100,
        wins=100,
        losses=50,
        current_clan_name="Clan X",
        days_since_last_any=0.0,
        days_since_last_effective=1.0,
        raw_7d=7,
        battle_utility=0.8,
        trend_ratio=1.5,
        activity_score=0.9,
        war_fetch_error=False,
        war_data_available=True,
        wars_analyzed=10,
        wars_participated=8,
        participation=0.8,
        fame_efficiency=0.7,
        consistency=0.8,
        war_utility=0.75,
        mean_fame_per_deck=220.0,
        candidate_score=0.82,
    )
    return PlayerScoutReport(**{**base.__dict__, **overrides})


def test_present_player_scout_builds_expected_sections():
    view_model = present_player_scout(_report())

    assert "Player One" in view_model.title_text
    assert "Level: 15" in view_model.profile_text
    assert "Recent activity: 0.90" in view_model.activity_text
    assert "Mode utility: 0.80" in view_model.utility_text
    assert "War utility: 0.75" in view_model.wars_text
    assert "Excellent candidate" in view_model.candidate_text


def test_present_player_scout_handles_missing_war_data():
    view_model = present_player_scout(_report(war_data_available=False, war_fetch_error=True))

    assert "unavailable" in view_model.wars_text.lower()
