from domain.scoring.battle_utility_score import compute_battle_utility


def test_zero_battles_returns_zero():
    assert compute_battle_utility(0, 0.0) == 0.0


def test_all_casual_returns_zero():
    # 10 batalhas, todas casual (weight 0.10 each)
    assert compute_battle_utility(10, 10 * 0.10) == 0.0


def test_all_ranked_returns_one():
    # 10 batalhas, todas ranked (weight 1.0 each)
    assert compute_battle_utility(10, 10 * 1.0) == 1.0


def test_all_events_returns_approx_072():
    # 10 batalhas, todas evento (weight 0.75 each)
    # (0.75 - 0.10) / 0.90 = 0.722...
    result = compute_battle_utility(10, 10 * 0.75)
    assert abs(result - 0.722) < 0.001


def test_mixed_half_ranked_half_casual():
    # 5 ranked (1.0) + 5 casual (0.10) = weighted 5.5, avg = 0.55
    # (0.55 - 0.10) / 0.90 = 0.5
    result = compute_battle_utility(10, 5.5)
    assert abs(result - 0.5) < 0.001


def test_result_always_between_zero_and_one():
    assert 0.0 <= compute_battle_utility(5, 5 * 0.75) <= 1.0
    assert 0.0 <= compute_battle_utility(1, 1.0) <= 1.0
