"""Fetch newest Blinkit Play Store reviews and merge them into data/raw_reviews.json.

Public data only (Play Store reviews), no login/API key required.
Safe to re-run: dedupes by reviewId so nothing is double-counted.
"""

import sys
from pathlib import Path

from google_play_scraper import Sort, reviews

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.io_utils import DATA_DIR, RAW_REVIEWS_PATH, load_json, save_json

APP_ID = "com.grofers.customerapp"  # Blinkit's live consumer app (legacy Grofers package name)
LANG = "en"
COUNTRY = "in"
FETCH_COUNT = 200  # newest reviews pulled per run


def fetch_latest() -> list[dict]:
    result, _ = reviews(
        APP_ID,
        lang=LANG,
        country=COUNTRY,
        sort=Sort.NEWEST,
        count=FETCH_COUNT,
    )
    return result


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_json(RAW_REVIEWS_PATH)

    fetched = fetch_latest()
    new_count = 0
    for r in fetched:
        review_id = r["reviewId"]
        if review_id in existing:
            continue
        existing[review_id] = {
            "reviewId": review_id,
            "userName": r.get("userName"),
            "content": r.get("content"),
            "score": r.get("score"),
            "at": r.get("at").isoformat() if r.get("at") else None,
            "thumbsUpCount": r.get("thumbsUpCount"),
            "appVersion": r.get("appVersion"),
        }
        new_count += 1

    save_json(RAW_REVIEWS_PATH, existing)

    print(f"Fetched {len(fetched)} reviews from Play Store, {new_count} new, "
          f"{len(existing)} total in {RAW_REVIEWS_PATH}")


if __name__ == "__main__":
    main()
