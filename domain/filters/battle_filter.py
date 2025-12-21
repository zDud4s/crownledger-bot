def battle_weight(battle: dict) -> float:
    """
    Peso (contribuição) desta batalha para a atividade.

    Objetivo:
    - NUNCA contar amigáveis/hosted/casuais -> 0.0
    - Contar ranked/ladder/pathOfLegend -> 1.0
    - Contar Challenge_* -> 1.0
    - (Opcional) Contar guerra (river race / clan war) -> 1.0
    - Restantes -> 0.0 (por segurança)
    """

    arena = battle.get("arena") or {}
    arena_name = (arena.get("name") or "").strip()

    btype = (battle.get("type") or "").strip()          # campo comum
    battle_type = (battle.get("battleType") or "").strip()  # nem sempre existe
    game_mode = battle.get("gameMode") or {}
    gm_name = (game_mode.get("name") or "").strip()

    btype_l = btype.lower()
    battle_type_l = battle_type.lower()
    gm_name_l = gm_name.lower()

    # 1) Nunca contar amigáveis / hosted / casual
    # Nota: alguns battlelogs usam arena.name == "Casual" para casuais/amigáveis.
    if arena_name == "Casual":
        return 0.0

    if btype_l in {"friendly", "hosted", "casual"}:
        return 0.0

    if "friendly" in battle_type_l or "hosted" in battle_type_l or "casual" in battle_type_l:
        return 0.0

    if "friendly" in gm_name_l or "hosted" in gm_name_l or "casual" in gm_name_l:
        return 0.0

    # 2) Ranked / ligas / troféus
    # Path of Legend
    if btype == "pathOfLegend":
        return 1.0

    # Trophy Road / Ladder costuma vir como gameMode.name == "Ladder" e type == "PvP"
    if gm_name_l == "ladder":
        return 1.0

    # 3) Challenges / events
    if gm_name.startswith("Challenge_"):
        return 1.0

    # 4) (Opcional) Guerra / River Race
    # Ativa se quiseres contar guerra como atividade válida.
    if btype_l.startswith("river") or btype_l.startswith("clanwar") or "river" in battle_type_l or "clanwar" in battle_type_l:
        return 1.0

    # 5) Restantes não contam
    return 0.0
