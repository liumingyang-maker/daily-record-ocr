"""Initialize the database - create all tables."""

import sys
from pathlib import Path

# Ensure project root is on sys.path so `app` is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import *  # noqa: F401,F403 - register all models
from app.infrastructure.database.session import engine


def init_db():
    Base.metadata.create_all(engine)
    print(f"Database initialized successfully at {engine.url}")


if __name__ == "__main__":
    init_db()
