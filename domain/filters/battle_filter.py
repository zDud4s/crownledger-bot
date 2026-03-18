def should_ignore_battle(battle: dict) -> bool:
    """
    Tipos que NUNCA devem contar (nem para totals, oldest, last_any, etc.).
    """
    btype = (battle.get("type") or "").strip()
    battle_type = (battle.get("battleType") or "").strip()
    gm = battle.get("gameMode") or {}
    gm_name = (gm.get("name") or "").strip()

    # normaliza para lower para apanhar variações
    btype_l = btype.lower()
    battle_type_l = battle_type.lower()
    gm_name_l = gm_name.lower()

    return (
        "boatBattle" in btype_l
        or "boatBattle" in battle_type_l
        or "boatBattle" in gm_name_l
    )

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

    CASUAL_WEIGHT = 0.10   # amigáveis / 1v1 — melhor que nada mas pouco valor
    EVENT_WEIGHT  = 0.75   # modos de evento legítimos (ex: Crazy Arena)

    # 1) Ranked / ligas / troféus (peso total)
    if btype == "pathOfLegend":
        return 1.0

    # Trophy Road / Ladder costuma vir como gameMode.name == "Ladder" e type == "PvP"
    if gm_name_l == "ladder":
        return 1.0

    # 2) Challenges / events (ranked)
    if gm_name.startswith("Challenge_"):
        return 1.0

    # 3) Guerra / River Race
    if btype_l.startswith("river") or btype_l.startswith("clanwar") or "river" in battle_type_l or "clanwar" in battle_type_l:
        return 1.0

    # 4) Modos de evento legítimos — atividade real, não é ranked mas conta muito
    # trail = Crazy Arena e outros modos de evento rotativos
    if btype_l == "trail":
        return EVENT_WEIGHT

    if "crazy" in gm_name_l or "pickmode" in gm_name_l:
        return EVENT_WEIGHT

    # 5) Amigáveis / 1v1 / hosted / casual — pouco valor
    if arena_name == "Casual":
        return CASUAL_WEIGHT

    if btype_l in {"friendly", "hosted", "casual"}:
        return CASUAL_WEIGHT

    if "friendly" in battle_type_l or "hosted" in battle_type_l or "casual" in battle_type_l:
        return CASUAL_WEIGHT

    if "friendly" in gm_name_l or "hosted" in gm_name_l or "casual" in gm_name_l:
        return CASUAL_WEIGHT

    # 6) Tipos desconhecidos — alguma atividade vale mais que nada
    return CASUAL_WEIGHT



