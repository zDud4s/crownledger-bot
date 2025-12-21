def rank_players(players):
    """
    Recebe lista de Player
    Devolve lista ordenada do mais ativo para o menos ativo
    """
    return sorted(
        players,
        key=lambda p: p.activity_score(),
        reverse=True
    )
