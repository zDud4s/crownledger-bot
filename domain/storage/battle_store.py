from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass
class StoredBattle:
    timestamp: datetime
    raw_json: dict[str, Any]


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _project_root() -> Path:
    # .../domain/storage/battle_store.py -> parents[2] = repo root (assumindo domain/ na raiz)
    return Path(__file__).resolve().parents[2]


def _sanitize_tag(tag: str) -> str:
    t = tag.strip().upper()
    if t.startswith("#"):
        t = t[1:]
    # manter apenas chars seguros
    safe = "".join(ch for ch in t if ch.isalnum())
    return safe or "UNKNOWN"


def _hash_battle(raw_json: dict[str, Any]) -> str:
    """
    Hash estável do payload inteiro da batalha para dedupe.
    """
    payload = json.dumps(raw_json, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def _parse_battle_time(s: str) -> datetime:
    """
    Clash Royale battleTime típico: '20200102T030405.000Z'
    """
    x = s.strip()
    if x.endswith("Z"):
        x = x[:-1]

    if "." in x:
        base, frac = x.split(".", 1)
    else:
        base, frac = x, "0"

    dt = datetime.strptime(base, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)

    frac_digits = "".join(ch for ch in frac if ch.isdigit())
    if frac_digits:
        frac_digits = (frac_digits + "000000")[:6]
        dt = dt.replace(microsecond=int(frac_digits))
    return dt


class BattleStore:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or (_project_root() / "data" / "battlelogs")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_player(self, player_tag: str) -> Path:
        fname = f"{_sanitize_tag(player_tag)}.jsonl"
        return self.base_dir / fname

    def upsert_player_battles(self, player_tag: str, battlelog_items: Iterable[dict[str, Any]]) -> int:
        """
        Adiciona apenas batalhas novas (dedupe por hash do raw_json).
        Retorna quantas foram adicionadas.
        """
        path = self._path_for_player(player_tag)
        existing_hashes = set()

        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        h = rec.get("hash")
                        if h:
                            existing_hashes.add(h)
                    except Exception:
                        continue

        added = 0
        with path.open("a", encoding="utf-8") as f:
            for item in battlelog_items:
                try:
                    bt = item.get("battleTime")
                    if not bt:
                        continue
                    ts = _parse_battle_time(bt)
                    h = _hash_battle(item)
                    if h in existing_hashes:
                        continue

                    rec = {
                        "hash": h,
                        "battleTime": bt,
                        "timestamp": _ensure_utc(ts).isoformat(),
                        "raw": item,
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    existing_hashes.add(h)
                    added += 1
                except Exception:
                    continue

        return added

    def load_player_battles(self, player_tag: str) -> list[StoredBattle]:
        """
        Carrega todas as batalhas guardadas do jogador.
        """
        path = self._path_for_player(player_tag)
        if not path.exists():
            return []

        battles: list[StoredBattle] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts = datetime.fromisoformat(rec["timestamp"])
                    raw = rec["raw"]
                    battles.append(StoredBattle(timestamp=_ensure_utc(ts), raw_json=raw))
                except Exception:
                    continue

        # ordenar por tempo
        battles.sort(key=lambda b: b.timestamp)
        return battles

    def list_players(self) -> list[str]:
        """
        Lista tags (sanitizadas) que existem no storage.
        Nota: aqui devolvemos o nome do ficheiro; normalmente vais mapear por tags reais no teu pipeline.
        """
        return [p.stem for p in self.base_dir.glob("*.jsonl")]
