"""Human-vs-LLM tagging agreement check — the quality metric for the whole
pipeline. This is a human-in-the-loop step, so it runs locally, not as part
of the nightly GitHub Action.

Usage (from the repo root, with GROQ_API_KEY not required for this script):

  python validation/spot_check.py sample
      Writes validation/spot_check_sample.csv with N randomly sampled
      already-tagged reviews. The llm_* columns are pre-filled from
      data/themes.json. Open the CSV, read each review, and fill in the
      human_categories / human_sentiment columns with YOUR OWN judgment
      (don't look at the llm_* columns while tagging, to keep it a fair
      comparison), then save.

  python validation/spot_check.py score
      Reads the filled-in CSV, compares your tags to the model's tags,
      computes an agreement percentage, and writes it into
      data/insights.json's "validation" block so the dashboard displays it.
"""

import argparse
import csv
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.io_utils import INSIGHTS_PATH, RAW_REVIEWS_PATH, THEMES_PATH, load_json, save_json

CSV_PATH = Path(__file__).resolve().parent / "spot_check_sample.csv"
DEFAULT_SAMPLE_SIZE = 20
FIELDNAMES = [
    "reviewId", "content", "llm_categories", "llm_sentiment",
    "human_categories", "human_sentiment",
]


def cmd_sample(n: int) -> None:
    themes = load_json(THEMES_PATH)
    raw_reviews = load_json(RAW_REVIEWS_PATH)

    if not themes:
        print("No tagged reviews found — run extract_themes.py first.")
        return

    eligible = list(themes.keys())
    n = min(n, len(eligible))
    sampled_ids = random.sample(eligible, n)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for rid in sampled_ids:
            t = themes[rid]
            categories = ";".join(sorted({s["category"] for s in t.get("category_signals", [])}))
            writer.writerow({
                "reviewId": rid,
                "content": raw_reviews.get(rid, {}).get("content", ""),
                "llm_categories": categories,
                "llm_sentiment": t.get("sentiment", ""),
                "human_categories": "",
                "human_sentiment": "",
            })

    print(f"Wrote {n} reviews to {CSV_PATH}")
    print("Open it, read the 'content' column, and fill in human_categories "
          "(semicolon-separated) and human_sentiment for each row based on "
          "your own read of the review — try not to peek at the llm_* "
          "columns until you're done. Then run: python validation/spot_check.py score")


def _normalize_categories(raw: str) -> set:
    return {c.strip() for c in raw.split(";") if c.strip()}


def cmd_score() -> None:
    if not CSV_PATH.exists():
        print(f"{CSV_PATH} not found — run 'sample' first.")
        return

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    scored_rows = [r for r in rows if r.get("human_categories", "").strip() or r.get("human_sentiment", "").strip()]

    if not scored_rows:
        print("No rows have human_categories/human_sentiment filled in yet — "
              "fill in the CSV before scoring.")
        return

    category_matches = 0
    sentiment_matches = 0
    full_matches = 0

    for row in scored_rows:
        human_cats = _normalize_categories(row.get("human_categories", ""))
        llm_cats = _normalize_categories(row.get("llm_categories", ""))
        human_sentiment = row.get("human_sentiment", "").strip().lower()
        llm_sentiment = row.get("llm_sentiment", "").strip().lower()

        cats_match = human_cats == llm_cats
        sentiment_match = human_sentiment == llm_sentiment

        category_matches += cats_match
        sentiment_matches += sentiment_match
        full_matches += cats_match and sentiment_match

    n = len(scored_rows)
    category_pct = round(100 * category_matches / n, 1)
    sentiment_pct = round(100 * sentiment_matches / n, 1)
    overall_pct = round(100 * full_matches / n, 1)

    print(f"Scored {n} reviews:")
    print(f"  Category agreement:  {category_pct}%")
    print(f"  Sentiment agreement: {sentiment_pct}%")
    print(f"  Full agreement:      {overall_pct}%")

    insights = load_json(INSIGHTS_PATH)
    insights["validation"] = {
        "agreement_pct": overall_pct,
        "category_agreement_pct": category_pct,
        "sentiment_agreement_pct": sentiment_pct,
        "last_spot_check_date": datetime.now(timezone.utc).date().isoformat(),
        "spot_check_sample_size": n,
    }
    save_json(INSIGHTS_PATH, insights)
    print(f"Wrote validation results into {INSIGHTS_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample_parser = subparsers.add_parser("sample", help="Draw a random sample to hand-tag")
    sample_parser.add_argument("--n", type=int, default=DEFAULT_SAMPLE_SIZE)

    subparsers.add_parser("score", help="Score the filled-in sample against the LLM's tags")

    args = parser.parse_args()
    if args.command == "sample":
        cmd_sample(args.n)
    elif args.command == "score":
        cmd_score()


if __name__ == "__main__":
    main()
