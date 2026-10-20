import asyncio
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.core.logging import logger

class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self._local = threading.local()
        self._lock = threading.Lock()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            self._local.conn = conn
        return self._local.conn

    def _execute_sync(self, query: str, params: Tuple = ()) -> int:
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            last_id = cur.lastrowid
            cur.close()
            return last_id or 0

    def _fetchall_sync(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            rows = [dict(row) for row in cur.fetchall()]
            cur.close()
            return rows

    def _fetchone_sync(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            row = cur.fetchone()
            cur.close()
            return dict(row) if row else None

    def _executescript_sync(self, script: str) -> None:
        with self._lock:
            conn = self._get_connection()
            conn.executescript(script)
            conn.commit()

    def _backup_sync(self, target_path: Path) -> None:
        with self._lock:
            conn = self._get_connection()
            target_path.parent.mkdir(parents=True, exist_ok=True)
            dest_conn = sqlite3.connect(str(target_path))
            with dest_conn:
                conn.backup(dest_conn)
            dest_conn.close()

    async def execute(self, query: str, params: Tuple = ()) -> int:
        return await asyncio.to_thread(self._execute_sync, query, params)

    async def fetchall(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetchall_sync, query, params)

    async def fetchone(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetchone_sync, query, params)

    async def executescript(self, script: str) -> None:
        await asyncio.to_thread(self._executescript_sync, script)

    async def backup(self, target_path: Path) -> None:
        await asyncio.to_thread(self._backup_sync, target_path)

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

db = Database()
