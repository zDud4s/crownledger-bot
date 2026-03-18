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
from domain.scoring.activity_score import compute_activity_score

class Player:
    def __init__(self, tag: str, name: str):
        self.tag = tag
        self.name = name
        self.battles = []

    def activity_snapshot(self):
        raw_battles = self.battles
        battles = filter_battles(raw_battles)
        removed = len(raw_battles) - len(battles)

        total = len(battles)
        effective_total = effective_battles_total(battles)
        effective_ratio_total = (effective_total / total) if total > 0 else 0.0

        return {
            "battles_total_fetched": total,
            "days_since_oldest": days_since_oldest_battle(battles),

            "effective_total": effective_total,
            "effective_ratio_total": effective_ratio_total,

            "days_since_last_any": days_since_last_any_battle(battles),
            "days_since_last_effective": days_since_last_effective_battle(battles),
            "days_with_battles": len({battle_timestamp(b).date() for b in battles}),

            "raw_7d": battles_in_last_days(battles, 7),
            "effective_7d": effective_battles_in_last_days(battles, 7),
            "weighted_7d": weighted_battles_in_last_days(battles, 7),
            "weighted_14d": weighted_battles_in_last_days(battles, 14),
            "weighted_2d": weighted_battles_in_last_days(battles, 2),

            # DEBUG: confirma que estás mesmo a remover boatBattle
            "ignored_battles_removed": removed,
        }

    def activity_score(self):
        return compute_activity_score(self.activity_snapshot())
