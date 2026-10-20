import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

import uvicorn
from app.core.config import settings

def main():
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
