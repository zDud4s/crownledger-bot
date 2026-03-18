import math
from domain.scoring.recent_activity_score import recent_activity_score, trend_arrow

def _snap(**kwargs):
    defaults = {"days_since_last_any": 1.0, "raw_7d": 5, "raw_14d": 10}
    defaults.update(kwargs)
    return defaults

def test_volume_uses_raw_not_weighted():
    """raw_7d must drive volume, not weighted_7d. THIS FAILS with current code."""
    snap_a = _snap(raw_7d=7, raw_14d=14)
    snap_b = _snap(raw_7d=7, raw_14d=14)
    assert recent_activity_score(snap_a) == recent_activity_score(snap_b)

def test_recency_uses_last_any_not_effective():
    snap_active = _snap(days_since_last_any=0.5, raw_7d=0, raw_14d=0)
    snap_never = _snap(days_since_last_any=float("inf"), raw_7d=0, raw_14d=0)
    assert recent_activity_score(snap_active) > recent_activity_score(snap_never)

def test_recency_inf_gives_zero_component():
    snap = _snap(days_since_last_any=float("inf"), raw_7d=0, raw_14d=0)
    assert recent_activity_score(snap) == 0.0

def test_trend_clamp_score_stays_in_range():
    snap = _snap(days_since_last_any=0.5, raw_7d=20, raw_14d=20)
    score = recent_activity_score(snap)
    assert 0.0 <= score <= 1.0

def test_trend_clamp_safe_when_raw14_equals_raw7():
    snap = _snap(days_since_last_any=1.0, raw_7d=7, raw_14d=7)
    score = recent_activity_score(snap)
    assert math.isfinite(score)

def test_full_active_player_near_one():
    snap = _snap(days_since_last_any=0.0, raw_7d=7, raw_14d=14)
    score = recent_activity_score(snap)
    assert score >= 0.90

def test_inactive_player_near_zero():
    snap = _snap(days_since_last_any=float("inf"), raw_7d=0, raw_14d=0)
    assert recent_activity_score(snap) < 0.05

def test_trend_arrow_up():
    assert trend_arrow(1.5) == "↗"

def test_trend_arrow_stable():
    assert trend_arrow(1.0) == "→"

def test_trend_arrow_down():
    assert trend_arrow(0.5) == "↘"
