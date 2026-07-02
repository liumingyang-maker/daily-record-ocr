from functools import lru_cache
from pathlib import Path
import yaml

CONFIGS_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_config(name: str) -> dict:
    path = CONFIGS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
