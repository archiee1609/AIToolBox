import datetime
import os
import shutil
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.database.connection import db
from app.schemas.system import BackupResponse

class BackupService:
    def list_backups(self) -> List[BackupResponse]:
        """Lists all existing verified database backups."""
        backup_dir = settings.backup_dir
        backups: List[BackupResponse] = []
        
        for f in backup_dir.glob("*.db"):
            stat = f.stat()
            backups.append(BackupResponse(
                filename=f.name,
                backup_path=str(f),
                size_bytes=stat.st_size,
                created_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
            ))
            
        backups.sort(key=lambda x: x.created_at, reverse=True)
        return backups

    async def create_backup(self) -> BackupResponse:
        """Performs a live hot backup of the SQLite database using SQLite backup API."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"workbench_backup_{timestamp}.db"
        dest_path = settings.backup_dir / backup_filename

        logger.info(f"Creating database backup at {dest_path}")
        await db.backup(dest_path)

        stat = dest_path.stat()
        return BackupResponse(
            filename=backup_filename,
            backup_path=str(dest_path),
            size_bytes=stat.st_size,
            created_at=datetime.datetime.now().isoformat()
        )

    def validate_backup(self, backup_filename: str) -> Dict[str, Any]:
        """Validates SQLite integrity and table presence in backup file."""
        target = settings.backup_dir / backup_filename
        if not target.exists():
            raise FileNotFoundError(f"Backup file '{backup_filename}' does not exist.")

        try:
            conn = sqlite3.connect(str(target))
            cur = conn.cursor()
            cur.execute("PRAGMA quick_check;")
            check_result = cur.fetchone()[0]
            if check_result != "ok":
                conn.close()
                return {"valid": False, "error": f"Integrity check failed: {check_result}"}

            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cur.fetchall()]
            conn.close()

            required = ["conversations", "messages", "workflows"]
            missing = [t for t in required if t not in tables]
            if missing:
                return {"valid": False, "error": f"Missing required tables in backup: {missing}"}

            return {"valid": True, "tables": tables, "size_bytes": target.stat().st_size}
        except Exception as e:
            return {"valid": False, "error": f"Invalid SQLite database: {str(e)}"}

    async def restore_backup(self, backup_filename: str, confirm: bool = False) -> Dict[str, Any]:
        """Restores a validated backup over the current application database."""
        if not confirm:
            raise ValueError("Restoration requires explicit user confirmation.")

        validation = self.validate_backup(backup_filename)
        if not validation["valid"]:
            raise ValueError(f"Cannot restore invalid backup: {validation.get('error')}")

        src = settings.backup_dir / backup_filename
        dest = settings.db_path

        # Close current connections
        db.close()

        # Create emergency pre-restore snapshot
        pre_restore = settings.backup_dir / "pre_restore_snapshot.db"
        shutil.copy2(dest, pre_restore)

        try:
            shutil.copy2(src, dest)
            # Remove any stale WAL/SHM files
            for ext in ["-wal", "-shm"]:
                wal_file = dest.with_name(dest.name + ext)
                if wal_file.exists():
                    wal_file.unlink()
        except Exception as e:
            # Revert to snapshot
            shutil.copy2(pre_restore, dest)
            raise RuntimeError(f"Restoration failed, reverted to pre-restore snapshot: {e}")

        return {
            "restored": True,
            "backup_filename": backup_filename,
            "message": "Database successfully restored from backup.",
            "tables_restored": validation.get("tables", [])
        }

backup_service = BackupService()
