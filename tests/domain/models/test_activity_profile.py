import pytest
from dataclasses import FrozenInstanceError

def _make_profile(**overrides):
    from domain.models.activity_profile import ActivityProfile
    defaults = dict(
        battles_total=30, raw_7d=7, raw_14d=14,
        days_with_battles=5, days_since_oldest=10.0,
        days_since_last_any=1.0, days_since_last_effective=2.0,
        weighted_7d=7.0, weighted_14d=14.0,
        activity_score=0.75, recent_activity_score=0.60, battle_utility=0.80,
    )
    defaults.update(overrides)
    return ActivityProfile(**defaults)

def test_instantiation_sets_all_fields():
    p = _make_profile()
    assert p.battles_total == 30
    assert p.raw_7d == 7
    assert p.raw_14d == 14
    assert p.days_with_battles == 5
    assert p.days_since_oldest == 10.0
    assert p.days_since_last_any == 1.0
    assert p.days_since_last_effective == 2.0
    assert p.weighted_7d == 7.0
    assert p.weighted_14d == 14.0
    assert p.activity_score == 0.75
    assert p.recent_activity_score == 0.60
    assert p.battle_utility == 0.80

def test_is_frozen():
    p = _make_profile()
    with pytest.raises(FrozenInstanceError):
        p.battles_total = 99
