from __future__ import annotations

import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Any, Iterable, Optional
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_battle(raw_json: dict[str, Any]) -> str:
    payload = json.dumps(raw_json, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


class SqliteStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path.as_posix())
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            clan_tag TEXT PRIMARY KEY,
            last_seen_at TEXT NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_tag TEXT PRIMARY KEY,
            last_seen_at TEXT NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS clan_memberships (
            clan_tag TEXT NOT NULL,
            player_tag TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            PRIMARY KEY (clan_tag, player_tag),
            FOREIGN KEY (clan_tag) REFERENCES clans(clan_tag) ON DELETE CASCADE,
            FOREIGN KEY (player_tag) REFERENCES players(player_tag) ON DELETE CASCADE
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS player_battles (
            player_tag TEXT NOT NULL,
            battle_time TEXT NOT NULL,
            battle_hash TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            PRIMARY KEY (player_tag, battle_hash),
            FOREIGN KEY (player_tag) REFERENCES players(player_tag) ON DELETE CASCADE
        );
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_player_battles_time ON player_battles(player_tag, battle_time);")
        self.conn.commit()

    def upsert_clan(self, clan_tag: str) -> None:
        now = _now_iso()
        self.conn.execute(
            "INSERT INTO clans(clan_tag, last_seen_at) VALUES(?, ?) "
            "ON CONFLICT(clan_tag) DO UPDATE SET last_seen_at=excluded.last_seen_at",
            (clan_tag, now),
        )
        self.conn.commit()

    def upsert_player(self, player_tag: str) -> None:
        now = _now_iso()
        self.conn.execute(
            "INSERT INTO players(player_tag, last_seen_at) VALUES(?, ?) "
            "ON CONFLICT(player_tag) DO UPDATE SET last_seen_at=excluded.last_seen_at",
            (player_tag, now),
        )
        self.conn.commit()

    def upsert_membership(self, clan_tag: str, player_tag: str) -> None:
        now = _now_iso()
        self.conn.execute(
            "INSERT INTO clan_memberships(clan_tag, player_tag, last_seen_at) VALUES(?, ?, ?) "
            "ON CONFLICT(clan_tag, player_tag) DO UPDATE SET last_seen_at=excluded.last_seen_at",
            (clan_tag, player_tag, now),
        )
        self.conn.commit()

    def get_latest_battle_time(self, player_tag: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT MAX(battle_time) FROM player_battles WHERE player_tag = ?",
            (player_tag,),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else None

    def insert_battles_delta(self, player_tag: str, battlelog_items: Iterable[dict[str, Any]]) -> int:
        """
        Insere apenas batalhas novas.
        Usa latest_battle_time para parar cedo (battlelog vem ordenado do mais recente para o mais antigo).
        """
        latest = self.get_latest_battle_time(player_tag)
        added = 0

        cur = self.conn.cursor()
        now = _now_iso()

        for item in battlelog_items:
            bt = item.get("battleTime")
            if not bt:
                continue

            if latest and bt <= latest:
                break

            h = _hash_battle(item)
            raw = json.dumps(item, ensure_ascii=False)

            try:
                cur.execute(
                    "INSERT OR IGNORE INTO player_battles(player_tag, battle_time, battle_hash, raw_json, ingested_at) "
                    "VALUES(?, ?, ?, ?, ?)",
                    (player_tag, bt, h, raw, now),
                )
                if cur.rowcount == 1:
                    added += 1
            except sqlite3.Error:
                continue

        self.conn.commit()
        return added
