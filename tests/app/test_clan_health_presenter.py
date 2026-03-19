from __future__ import annotations

from app.presenters.clan_health_presenter import present_clan_health
from app.use_cases.clan_health import ClanHealthReport, PlayerHealth


def _player(
    *,
    name: str,
    tag: str,
    score: float,
    days_since_last_any: float,
    raw_7d: int,
    trend_ratio: float | None,
    battle_utility: float,
) -> PlayerHealth:
    return PlayerHealth(
        name=name,
        tag=tag,
        score=score,
        days_since_last_any=days_since_last_any,
        days_since_last_effective=days_since_last_any,
        raw_7d=raw_7d,
        trend_ratio=trend_ratio,
        battle_utility=battle_utility,
    )


def test_present_clan_health_hides_active_rows_when_disabled():
    report = ClanHealthReport(
        clan_tag="#ABC123",
        total_members=3,
        inactive=[_player(name="A", tag="#A", score=0.10, days_since_last_any=7.0, raw_7d=0, trend_ratio=None, battle_utility=0.20)],
        at_risk=[_player(name="B", tag="#B", score=0.40, days_since_last_any=2.0, raw_7d=3, trend_ratio=1.0, battle_utility=0.50)],
        active=[_player(name="C", tag="#C", score=0.80, days_since_last_any=0.1, raw_7d=7, trend_ratio=1.5, battle_utility=0.90)],
    )

    view_model = present_clan_health(report, show_active=False)

    assert view_model.total_members == 3
    assert len(view_model.rows) == 2
    assert [row.name for row in view_model.rows] == ["A", "B"]


def test_present_clan_health_formats_summary_and_rows():
    report = ClanHealthReport(
        clan_tag="#ABC123",
        total_members=1,
        inactive=[],
        at_risk=[],
        active=[_player(name="C", tag="#C", score=0.80, days_since_last_any=0.01, raw_7d=7, trend_ratio=1.5, battle_utility=0.90)],
    )

    view_model = present_clan_health(report, show_active=True)

    assert "Clan #ABC123" in view_model.summary_text
    assert view_model.rows[0].tier_label == "Active"
    assert view_model.rows[0].days_since_last_any_text == "Today"
    assert view_model.rows[0].trend_text
