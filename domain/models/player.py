from domain.metrics.activity_metrics import (
    filter_battles,
    battle_timestamp,
    days_since_oldest_battle,
    days_since_last_any_battle,
    days_since_last_effective_battle,
    battles_in_last_days,
    effective_battles_in_last_days,
    weighted_battles_in_last_days,
    effective_battles_total,
)
from domain.models.activity_profile import ActivityProfile
from domain.scoring.activity_score import compute_activity_score
from domain.scoring.recent_activity_score import recent_activity_score
from domain.scoring.battle_utility_score import compute_battle_utility


class Player:
    def __init__(self, tag: str, name: str):
        self.tag = tag
        self.name = name
        self.battles = []

    def activity_profile(self) -> ActivityProfile:
        """Returns a fully-populated ActivityProfile (typed dataclass)."""
        raw_battles = self.battles
        battles = filter_battles(raw_battles)

        total = len(battles)
        raw_7d = battles_in_last_days(battles, 7)
        raw_14d = battles_in_last_days(battles, 14)
        days_with = len({battle_timestamp(b).date() for b in battles})
        days_oldest = days_since_oldest_battle(battles)
        days_any = days_since_last_any_battle(battles)
        days_eff = days_since_last_effective_battle(battles)
        w7 = weighted_battles_in_last_days(battles, 7)
        w14 = weighted_battles_in_last_days(battles, 14)

        # Build temporary dict for scoring functions (duck-typed)
        _snap = {
            "battles_total": total,
            "days_since_oldest": days_oldest,
            "days_since_last_any": days_any,
            "days_since_last_effective": days_eff,
            "raw_7d": raw_7d,
            "raw_14d": raw_14d,
            "weighted_7d": w7,
            "weighted_14d": w14,
        }

        act_score = compute_activity_score(_snap)
        rec_score = recent_activity_score(_snap)
        utility = compute_battle_utility(raw_14d, w14)

        return ActivityProfile(
            battles_total=total,
            raw_7d=raw_7d,
            raw_14d=raw_14d,
            days_with_battles=days_with,
            days_since_oldest=days_oldest,
            days_since_last_any=days_any,
            days_since_last_effective=days_eff,
            weighted_7d=w7,
            weighted_14d=w14,
            activity_score=act_score,
            recent_activity_score=rec_score,
            battle_utility=utility,
        )

    def activity_snapshot(self) -> dict:
        """
        Backward-compatible dict snapshot for legacy consumers (rank_clan.py, etc.).
        Computes from activity_profile() to avoid duplication.
        """
        p = self.activity_profile()
        return {
            "battles_total": p.battles_total,
            "battles_total_fetched": p.battles_total,  # old name alias
            "days_since_oldest": p.days_since_oldest,
            "days_since_last_any": p.days_since_last_any,
            "days_since_last_effective": p.days_since_last_effective,
            "days_with_battles": p.days_with_battles,
            "raw_7d": p.raw_7d,
            "raw_14d": p.raw_14d,
            "weighted_7d": p.weighted_7d,
            "weighted_14d": p.weighted_14d,
            "battle_utility": p.battle_utility,
            # Legacy: effective_7d kept for any remaining consumers
            "effective_7d": effective_battles_in_last_days(
                filter_battles(self.battles), 7
            ),
        }

    def activity_score(self) -> float:
        return self.activity_profile().activity_score
