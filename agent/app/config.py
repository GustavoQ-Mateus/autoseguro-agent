from __future__ import annotations
import os
from pathlib import Path

QUOTE_SERVICE_URL = os.getenv("QUOTE_SERVICE_URL", "http://localhost:8000")
QUOTE_TIMEOUT_SECONDS = float(os.getenv("QUOTE_TIMEOUT_SECONDS", "5"))
QUOTE_MAX_ATTEMPTS = int(os.getenv("QUOTE_MAX_ATTEMPTS", "3"))
QUOTE_BACKOFF_SECONDS = float(os.getenv("QUOTE_BACKOFF_SECONDS", "1"))

STAGNATION_LIMIT = int(os.getenv("STAGNATION_LIMIT", "3"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_TIMEOUT_SECONDS = float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "15"))

DB_PATH = Path(os.getenv("AGENT_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "agent.db")))
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "data" / "schema.sql"

HISTORY_LIMIT = int(os.getenv("AGENT_HISTORY_LIMIT", "10"))
