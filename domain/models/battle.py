class Battle:
    def __init__(self, timestamp, battle_type, raw_json=None):
        self.timestamp = timestamp
        self.battle_type = battle_type
        self.raw_json = raw_json or {}
