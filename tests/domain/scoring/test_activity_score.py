from domain.scoring.activity_score import compute_activity_score, _span_factor

def test_casual_and_ranked_same_score_same_volume():
    """
    Players with equal volume and recency must have the same activity_score,
    regardless of battle type. THIS TEST FAILS with current code (uses effective_ratio).
    """
    snap_high_ratio = {
        "battles_total": 40,
        "days_since_oldest": 3.0,
        "effective_ratio_total": 1.0,   # old field — must be ignored
    }
    snap_low_ratio = {
        "battles_total": 40,
        "days_since_oldest": 3.0,
        "effective_ratio_total": 0.0,   # old field — must be ignored
    }
    assert compute_activity_score(snap_high_ratio) == compute_activity_score(snap_low_ratio)

def test_under_30_quadratic():
    snap = {"battles_total": 15, "days_since_oldest": 1.0}
    score = compute_activity_score(snap)
    expected = round(0.5 * (15 / 30) ** 2, 3)
    assert score == expected

def test_exactly_30_with_fresh_battles_near_1():
    snap = {"battles_total": 30, "days_since_oldest": 0.5}  # span ~ 1.0
    score = compute_activity_score(snap)
    assert score > 0.99

def test_exactly_30_with_stale_battles_floors_at_half():
    snap = {"battles_total": 30, "days_since_oldest": 15.0}  # span = 0.0
    score = compute_activity_score(snap)
    assert score == 0.5

def test_zero_battles_returns_zero():
    assert compute_activity_score({"battles_total": 0, "days_since_oldest": 0.0}) == 0.0

def test_accepts_new_field_name_battles_total():
    """Accepts 'battles_total' (new) without 'battles_total_fetched' (old)."""
    snap = {"battles_total": 35, "days_since_oldest": 2.0}
    score = compute_activity_score(snap)
    assert score > 0.5

def test_backward_compat_battles_total_fetched():
    """Accepts 'battles_total_fetched' for backward-compat."""
    snap = {"battles_total_fetched": 35, "days_since_oldest": 2.0}
    score = compute_activity_score(snap)
    assert score > 0.5

def test_span_factor_full_at_2_days():
    assert _span_factor(2.0) == 1.0

def test_span_factor_zero_at_15_days():
    assert _span_factor(15.0) == 0.0

def test_span_factor_inf_returns_zero():
    assert _span_factor(float("inf")) == 0.0
