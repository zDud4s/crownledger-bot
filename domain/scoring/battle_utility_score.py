def compute_battle_utility(raw_14d: int, weighted_14d: float) -> float:
    """
    Mede a distribuição de modos de jogo nas últimas 2 semanas.

    Pesos definidos em battle_filter.py:
      CASUAL_WEIGHT  = 0.10  (friendly, hosted, casual, unknown)
      EVENT_WEIGHT   = 0.75  (trail/crazy arena/pick mode)
      RANKED_WEIGHT  = 1.00  (pathOfLegend, ladder, challenge, riverrace)

    Exemplos de resultado:
      0.00 → 100% batalhas casuais (weight 0.10)
      0.72 → 100% batalhas de evento (weight 0.75)
      1.00 → 100% ranked/war/challenge (weight 1.00)
    """
    if raw_14d == 0:
        return 0.0
    avg_weight = weighted_14d / raw_14d    # intervalo: 0.10 → 1.0
    return max(0.0, (avg_weight - 0.10) / 0.90)
