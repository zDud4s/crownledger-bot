from domain.metrics.activity_metrics import (
    days_since_last_any_battle,
    days_since_last_effective_battle,
    battles_in_last_days,
    effective_battles_in_last_days,
    weighted_battles_in_last_days,
)
from domain.scoring.activity_score import compute_activity_score


class Player:
    def __init__(self, tag: str, name: str):
        self.tag = tag
        self.name = name
        self.battles = []

    def activity_snapshot(self):
        return {
            "battles_total_fetched": len(self.battles),
            "days_since_last_any": days_since_last_any_battle(self.battles),
            "days_since_last_effective": days_since_last_effective_battle(self.battles),
            "days_with_battles": len({b.timestamp.date() for b in self.battles}),

            "raw_7d": battles_in_last_days(self.battles, 7),
            "effective_7d": effective_battles_in_last_days(self.battles, 7),

            "weighted_7d": weighted_battles_in_last_days(self.battles, 7),
            "weighted_2d": weighted_battles_in_last_days(self.battles, 2),
        }

    def activity_score(self, clan_baseline: dict | None = None):
        snapshot = self.activity_snapshot()
        return compute_activity_score(snapshot, clan_baseline=clan_baseline)