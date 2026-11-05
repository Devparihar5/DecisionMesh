"""Environment configuration, shared by transport and execution services."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    agent_timeout_seconds: float = 180
    frontend_origin: str = "http://127.0.0.1:5173"
    database_path: Path = PROJECT_ROOT / "data" / "decisionmesh.sqlite3"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        return cls(
            llm_base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/"),
            llm_api_key=os.getenv("LLM_API_KEY", "local"),
            llm_model=os.getenv("LLM_MODEL", "").strip(),
            agent_timeout_seconds=float(os.getenv("AGENT_TIMEOUT_SECONDS", "180")),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173"),
            database_path=Path(os.getenv("MEMORY_DB_PATH", str(PROJECT_ROOT / "data" / "decisionmesh.sqlite3"))).expanduser(),
        )
