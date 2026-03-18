from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityProfile:
    # Volume (contagens brutas, sem pesos de modo)
    battles_total: int      # anteriormente "battles_total_fetched" no snapshot dict
    raw_7d: int
    raw_14d: int
    days_with_battles: int

    # Tempo
    days_since_oldest: float
    days_since_last_any: float
    days_since_last_effective: float   # informativo — não usado nos scores de atividade

    # Pesos (apenas para battle_utility)
    weighted_7d: float
    weighted_14d: float

    # Scores computados
    activity_score: float          # 0–1, volume + recência pura
    recent_activity_score: float   # 0–1, últimas 2 semanas
    battle_utility: float          # 0–1, qualidade de modos (14 dias)
