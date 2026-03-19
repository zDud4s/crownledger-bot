from __future__ import annotations

import pytest

from app.input_normalizers import clamp_int, normalize_clan_tag, normalize_player_tag


def test_normalize_clan_tag_adds_hash_and_uppercases():
    assert normalize_clan_tag("abc123") == "#ABC123"


def test_normalize_player_tag_keeps_hash():
    assert normalize_player_tag("#ab12") == "#AB12"


def test_normalize_tag_rejects_blank_value():
    with pytest.raises(ValueError):
        normalize_clan_tag("   ")


def test_clamp_int_limits_to_bounds():
    assert clamp_int(0, 1, 10) == 1
    assert clamp_int(11, 1, 10) == 10
    assert clamp_int(5, 1, 10) == 5
