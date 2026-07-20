"""Pass B: aggregate themes.json in Python (ground truth), then ask Groq to
write the narrative on top of those pre-computed numbers.

Every count AND every category selection/ranking that ends up on the
dashboard is decided here in Python, never by the model. The model's only
job is to write short rationale text from evidence it's handed — it cannot
choose which categories make the list, reorder them, or invent a count.
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from groq import Groq

from io_utils import INSIGHTS_PATH, RAW_REVIEWS_PATH, THEMES_PATH, load_json, save_json
from prompts import CATEGORY_TAXONOMY, RESEARCH_QUESTIONS, build_synthesis_prompt

MODEL = "llama-3.3-70b-versatile"
QUOTES_PER_CATEGORY = 3
QUOTES_PER_POOL = 15
LOW_CONFIDENCE_THRESHOLD = 50
TOP_N_CATEGORIES = 10

# unmet_need_or_friction and curious_exploring both indicate "worth exploring
# / not yet satisfied" — habitual_purchase indicates "already doing this,"
# which is the opposite of what a discovery recommendation should surface.
EXPLORE_WORTHY_RELATIONSHIPS = {"unmet_need_or_friction", "curious_exploring"}


def build_aggregates(themes: dict) -> dict:
    category_signal_counts: dict[str, Counter] = defaultdict(Counter)
    segment_counts = Counter()
    sentiment_counts = Counter()
    discovery_channel_counts = Counter()
    habit_true = 0
    habit_false = 0
    friction_count = 0
    unmet_need_count = 0

    for t in themes.values():
        for signal in t.get("category_signals", []):
            cat = signal.get("category")
            rel = signal.get("relationship")
            if cat in CATEGORY_TAXONOMY and rel:
                category_signal_counts[cat][rel] += 1
        segment_counts[t.get("segment_signal", "unclear")] += 1
        sentiment_counts[t.get("sentiment", "neutral")] += 1
        discovery_channel_counts[t.get("discovery_channel", "none_mentioned")] += 1
        if t.get("habit_signal"):
            habit_true += 1
        else:
            habit_false += 1
        if t.get("friction_point"):
            friction_count += 1
        if t.get("unmet_need"):
            unmet_need_count += 1

    category_summary = {}
    for cat in CATEGORY_TAXONOMY:
        counts = category_signal_counts.get(cat, Counter())
        explore_worthy = sum(counts[r] for r in EXPLORE_WORTHY_RELATIONSHIPS)
        total = sum(counts.values())
        if total:
            category_summary[cat] = {
                "habitual_purchase": counts.get("habitual_purchase", 0),
                "unmet_need_or_friction": counts.get("unmet_need_or_friction", 0),
                "curious_exploring": counts.get("curious_exploring", 0),
                "explore_worthy_count": explore_worthy,
                "total_count": total,
            }

    return {
        "sample_size": len(themes),
        "category_summary": category_summary,
        "segment_counts": dict(segment_counts),
        "sentiment_counts": dict(sentiment_counts),
        "discovery_channel_counts": dict(discovery_channel_counts),
        "habit_signal_true_count": habit_true,
        "habit_signal_false_count": habit_false,
        "friction_mentioned_count": friction_count,
        "unmet_need_mentioned_count": unmet_need_count,
        # Explicit evidence count each research question must cite —
        # the model is instructed not to substitute a different number.
        "research_question_evidence_counts": {
            "q1_repeat_categories": habit_true,
            "q2_exploration_blockers": friction_count,
            "q3_discovery_channels": sum(
                v for k, v in discovery_channel_counts.items() if k != "none_mentioned"
            ),
            "q4_habit_role": habit_true,
            "q5_info_needed": unmet_need_count,
            "q6_recurring_frustrations": friction_count,
            "q7_experimenting_segments": segment_counts.get("explorer", 0),
            "q8_unmet_needs": unmet_need_count,
        },
    }


def rank_top_categories(aggregates: dict, themes: dict, raw_reviews: dict) -> list[dict]:
    """Python fully decides which categories make the list, their rank, and
    their evidence — ranked by explore-worthy signal (unmet need/friction/
    curiosity), not by raw popularity, so "top categories" means "worth
    nudging users toward" rather than "already popular."
    """

    def content_for(review_id: str) -> str:
        return (raw_reviews.get(review_id, {}).get("content") or "").strip()

    ranked = sorted(
        aggregates["category_summary"].items(),
        key=lambda kv: (kv[1]["explore_worthy_count"], kv[1]["total_count"], kv[0]),
        reverse=True,
    )[:TOP_N_CATEGORIES]

    result = []
    for category, counts in ranked:
        # Prefer quotes that actually show unmet need / friction / curiosity;
        # only fall back to habitual-purchase quotes if nothing else exists.
        priority_ids = [
            rid
            for rid, t in themes.items()
            if any(
                s.get("category") == category and s.get("relationship") in EXPLORE_WORTHY_RELATIONSHIPS
                for s in t.get("category_signals", [])
            )
            and content_for(rid)
        ]
        fallback_ids = [
            rid
            for rid, t in themes.items()
            if any(s.get("category") == category and s.get("relationship") == "habitual_purchase" for s in t.get("category_signals", []))
            and content_for(rid)
            and rid not in priority_ids
        ]
        quotes = [content_for(rid) for rid in (priority_ids + fallback_ids)[:QUOTES_PER_CATEGORY]]

        result.append({
            "category": category,
            "evidence_count": counts["explore_worthy_count"],
            "total_mentions": counts["total_count"],
            "quotes": quotes,
        })
    return result


def collect_sample_quotes(themes: dict, raw_reviews: dict) -> dict:
    def content_for(review_id: str) -> str:
        return (raw_reviews.get(review_id, {}).get("content") or "").strip()

    frustration_quotes = [
        {"quote": content_for(rid), "friction": t["friction_point"]}
        for rid, t in themes.items()
        if t.get("friction_point") and content_for(rid)
    ][:QUOTES_PER_POOL]

    unmet_need_quotes = [
        {"quote": content_for(rid), "unmet_need": t["unmet_need"]}
        for rid, t in themes.items()
        if t.get("unmet_need") and content_for(rid)
    ][:QUOTES_PER_POOL]

    habit_quotes = [
        {"quote": content_for(rid), "reason": t.get("habit_reason")}
        for rid, t in themes.items()
        if t.get("habit_signal") and content_for(rid)
    ][:QUOTES_PER_POOL]

    discovery_quotes = [
        {"quote": content_for(rid), "channel": t.get("discovery_channel")}
        for rid, t in themes.items()
        if t.get("discovery_channel") not in (None, "none_mentioned") and content_for(rid)
    ][:QUOTES_PER_POOL]

    return {
        "frustrations": frustration_quotes,
        "unmet_needs": unmet_need_quotes,
        "habits": habit_quotes,
        "discovery_channels": discovery_quotes,
    }


def main() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY environment variable is not set")

    themes = load_json(THEMES_PATH)
    raw_reviews = load_json(RAW_REVIEWS_PATH)

    if not themes:
        print("No tagged reviews yet — run extract_themes.py first.")
        return

    aggregates = build_aggregates(themes)
    ranked_categories = rank_top_categories(aggregates, themes, raw_reviews)
    sample_quotes = collect_sample_quotes(themes, raw_reviews)

    client = Groq(api_key=api_key)
    messages = build_synthesis_prompt(ranked_categories, aggregates, sample_quotes)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    narrative = json.loads(response.choices[0].message.content)

    # Rationale text comes from the model; category, rank, evidence_count,
    # and quotes stay exactly what Python computed above, regardless of
    # anything the model's JSON says.
    rationale_by_category = {
        r.get("category"): r.get("rationale", "")
        for r in narrative.get("category_rationales", [])
    }
    top_10_categories = [
        {**cat, "rationale": rationale_by_category.get(cat["category"], "")}
        for cat in ranked_categories
    ]

    # Force evidence_count for research questions to the Python-computed
    # ground truth even if the model's JSON drifted, so the dashboard can
    # never show a number that didn't come from real aggregation.
    qa = narrative.get("research_questions", {})
    for key, evidence_count in aggregates["research_question_evidence_counts"].items():
        if key in qa:
            qa[key]["evidence_count"] = evidence_count

    insights = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": aggregates["sample_size"],
        "low_confidence": aggregates["sample_size"] < LOW_CONFIDENCE_THRESHOLD,
        "aggregates": aggregates,
        "top_10_categories": top_10_categories,
        "research_questions": qa,
        "validation": load_json(INSIGHTS_PATH).get("validation", {
            "agreement_pct": None,
            "last_spot_check_date": None,
            "spot_check_sample_size": None,
        }),
    }

    save_json(INSIGHTS_PATH, insights)
    print(f"Wrote insights for {aggregates['sample_size']} reviews to {INSIGHTS_PATH}")


if __name__ == "__main__":
    main()
