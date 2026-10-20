import sys
import asyncio
import pytest
from pathlib import Path

# Add backend directory to sys.path so 'app' is importable directly
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.migrations import run_migrations

@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Initializes the database schema before running tests."""
    asyncio.run(run_migrations())
