from __future__ import annotations

from app.presenters.war_rank_presenter import present_war_rank
from app.use_cases.war_rank import WarPlayerStats


def _player(
    *,
    name: str,
    tag: str,
    war_utility: float,
    wars_participated: int,
    total_wars: int,
    participation: float,
    consistency: float,
    mean_fame_per_deck: float,
) -> WarPlayerStats:
    return WarPlayerStats(
        tag=tag,
        name=name,
        wars_participated=wars_participated,
        total_wars=total_wars,
        participation=participation,
        fame_efficiency=0.0,
        consistency=consistency,
        war_utility=war_utility,
        mean_fame_per_deck=mean_fame_per_deck,
    )


def test_present_war_rank_builds_summary_and_rows():
    players = [
        _player(
            name="Alpha",
            tag="#AAA",
            war_utility=0.82,
            wars_participated=4,
            total_wars=5,
            participation=0.8,
            consistency=0.8,
            mean_fame_per_deck=221.4,
        ),
        _player(
            name="Bravo",
            tag="#BBB",
            war_utility=0.41,
            wars_participated=2,
            total_wars=5,
            participation=0.5,
            consistency=0.4,
            mean_fame_per_deck=140.8,
        ),
    ]

    view_model = present_war_rank("#CLAN", 5, players)

    assert "Clan #CLAN" in view_model.summary_text
    assert len(view_model.rows) == 2
    assert view_model.rows[0].rank_text == "1"
    assert view_model.rows[0].tier_label == "Strong"
    assert view_model.rows[1].tier_label == "Low"


def test_present_war_rank_handles_empty_list():
    view_model = present_war_rank("#CLAN", 5, [])

    assert view_model.actual_wars == 0
    assert view_model.total_players == 0
    assert view_model.rows == []
