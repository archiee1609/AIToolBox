# Database Backup & Recovery Guide

## Overview
Local AI Workbench persists all user data in a local SQLite database (`data/workbench.db`).

The storage engine runs in Write-Ahead Logging (WAL) mode (`PRAGMA journal_mode=WAL;`), enabling non-blocking concurrent reads and ACID-compliant writes.

---

## 1. Creating a Hot Backup
You can create an instant snapshot of your database without stopping the application:
1. Navigate to **Settings** in the left sidebar.
2. Under **SQLite Hot Backups & Disaster Recovery**, click **Create New Backup**.
3. The backend uses the official SQLite Online Backup API (`sqlite3.Connection.backup`) to cleanly copy database pages to:
   ```
   data/backups/workbench_backup_YYYYMMDD_HHMMSS.db
   ```
4. The backup file appears immediately in the table with its size and creation timestamp.

---

## 2. Restoring a Backup
Before restoring, the backend automatically runs validation checks:
1. **Integrity Check**: Executes `PRAGMA quick_check;` to verify database health.
2. **Schema Verification**: Confirms that required tables (`conversations`, `messages`, `workflows`) exist.
3. **Emergency Pre-Restore Snapshot**: The backend saves a copy of the active database before overwriting.
4. If confirmed by the user, the database is restored and stale WAL/SHM locks are purged.

---

## 3. Manual Export & Reset
* **To export conversations or diagnostics**: Navigate to **Diagnostics** and click **Export Diagnostics (JSON)**.
* **To reset all application data**: Stop the application (`scripts/stop.bat`), and delete `data/workbench.db`. The application will automatically initialize a fresh database upon next launch.
