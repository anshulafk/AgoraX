import os
import yaml
from pathlib import Path
from pydantic_settings import BaseSettings

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.yaml"

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./trading_engine.db"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"

# Load YAML Config
def load_yaml_config(path: Path) -> dict:
    with open(path, "r") as file:
        return yaml.safe_load(file)

config_yaml = load_yaml_config(CONFIG_FILE)

settings = Settings()
