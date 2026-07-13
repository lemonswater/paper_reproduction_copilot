from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv("OPENAI_MODEL", "mimo-v2.5-pro")
    embedding_api_key: Optional[str] = os.getenv("EMBEDDING_API_KEY")
    embedding_base_url: Optional[str] = os.getenv("EMBEDDING_BASE_URL")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "qwen-text-embedding-v4")
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
    max_steps: int = int(os.getenv("MAX_STEPS", "20"))


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
