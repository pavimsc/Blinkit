"""Pass A: tag each new review against a fixed schema via Groq (Llama 3.3 70B).

Idempotent — only reviews not already present in themes.json are sent to the
model, so re-running never re-spends tokens on already-tagged reviews.
"""

import json
import os

from groq import Groq

from io_utils import RAW_REVIEWS_PATH, THEMES_PATH, load_json, save_json
from prompts import build_extraction_prompt

MODEL = "llama-3.3-70b-versatile"
BATCH_SIZE = 12


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY environment variable is not set")

    client = Groq(api_key=api_key)

    raw_reviews = load_json(RAW_REVIEWS_PATH)
    themes = load_json(THEMES_PATH)

    pending = [r for rid, r in raw_reviews.items() if rid not in themes and r.get("content")]

    if not pending:
        print("No new reviews to tag — themes.json is already up to date.")
        return

    tagged_count = 0
    for batch in chunked(pending, BATCH_SIZE):
        messages = build_extraction_prompt(batch)
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
            parsed = json.loads(response.choices[0].message.content)
        except Exception as exc:  # network/parse failure on one batch shouldn't kill the run
            print(f"Skipping a batch of {len(batch)} reviews due to error: {exc}")
            continue

        for result in parsed.get("results", []):
            review_id = result.get("reviewId")
            if not review_id:
                continue
            themes[review_id] = result
            tagged_count += 1

        save_json(THEMES_PATH, themes)  # persist after every batch for resilience

    print(f"Tagged {tagged_count} new reviews. {len(themes)} total in {THEMES_PATH}")


if __name__ == "__main__":
    main()
