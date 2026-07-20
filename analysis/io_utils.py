"""Shared JSON load/save helpers and data paths used across the analysis pipeline."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
RAW_REVIEWS_PATH = DATA_DIR / "raw_reviews.json"
THEMES_PATH = DATA_DIR / "themes.json"
INSIGHTS_PATH = DATA_DIR / "insights.json"


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
