from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv("OPENAI_MODEL", "mimo-v2.5-pro")
    embedding_api_key: Optional[str] = os.getenv("EMBEDDING_API_KEY")
    embedding_base_url: Optional[str] = os.getenv("EMBEDDING_BASE_URL")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "qwen-text-embedding-v4")
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
    runs_dir: Path = Path(os.getenv("RUNS_DIR", "runs"))
    checkpoint_db_path: Path = Path(
        os.getenv("CHECKPOINT_DB_PATH", "checkpoints/langgraph.sqlite")
    )
    max_steps: int = int(os.getenv("MAX_STEPS", "20"))

    execution_profiles_path: Path = Path(
        os.getenv(
            "EXECUTION_PROFILES_PATH",
            "config/execution_profiles.local.json"
        )
    )
    default_execution_profile: str = os.getenv(
        "DEFAULT_EXECUTION_PROFILE",
        "local",
    )

    smoke_test_timeout_seconds: int = int(
        os.getenv("SMOKE_TEST_TIMEOUT_SECONDS", "60")
    )

    max_repair_attempts: int = int(
        os.getenv("MAX_REPAIR_ATTEMPTS", "1")
    )


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.runs_dir.mkdir(parents=True, exist_ok=True)
settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)