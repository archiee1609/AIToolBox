import pytest
from app.database.connection import db
from app.database.migrations import run_migrations
from app.services.backup_service import backup_service
from app.core.config import settings

@pytest.mark.asyncio
async def test_database_migrations_and_crud():
    # Run migrations
    await run_migrations()

    # Insert test preference
    await db.execute(
        "INSERT INTO user_preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("test_key", "test_value")
    )

    row = await db.fetchone("SELECT value FROM user_preferences WHERE key = ?", ("test_key",))
    assert row is not None
    assert row["value"] == "test_value"

@pytest.mark.asyncio
async def test_backup_and_validation():
    # Create backup
    backup = await backup_service.create_backup()
    assert backup.filename.startswith("workbench_backup_")

    # Validate backup
    val = backup_service.validate_backup(backup.filename)
    assert val["valid"] is True
    assert "conversations" in val["tables"]
    assert "messages" in val["tables"]

    # Clean up backup
    backup_file = settings.backup_dir / backup.filename
    if backup_file.exists():
        backup_file.unlink()
