"""Prompt templates and the fixed taxonomy/schema for the two-pass analysis."""

# Reviews are tagged against this fixed list so category counts are comparable
# across nights, instead of the model inventing free-text category names.
CATEGORY_TAXONOMY = [
    "Groceries & Staples",
    "Fruits & Vegetables",
    "Dairy & Bakery",
    "Snacks & Beverages",
    "Personal Care",
    "Beauty & Cosmetics",
    "Health & Wellness",
    "Baby Care",
    "Pet Supplies",
    "Home & Kitchen Needs",
    "Cleaning & Household Supplies",
    "Electronics Accessories",
    "Stationery & Office",
    "Fashion & Apparel Accessories",
]

RESEARCH_QUESTIONS = {
    "q1_repeat_categories": "Why do users repeatedly buy from the same categories?",
    "q2_exploration_blockers": "What prevents users from exploring new categories?",
    "q3_discovery_channels": "How do users discover products today?",
    "q4_habit_role": "What role do habits play in shopping behavior?",
    "q5_info_needed": "What information do users need before trying a new category?",
    "q6_recurring_frustrations": "What frustrations emerge repeatedly?",
    "q7_experimenting_segments": "Which user segments are more likely to experiment?",
    "q8_unmet_needs": "What unmet needs emerge consistently across discussions?",
}


def build_extraction_prompt(batch: list[dict]) -> list[dict]:
    """Pass A: tag each review in the batch against a fixed schema."""
    taxonomy_list = ", ".join(CATEGORY_TAXONOMY)
    reviews_block = "\n".join(
        f'- reviewId: "{r["reviewId"]}" | rating: {r.get("score")} | text: "{r.get("content", "").strip()}"'
        for r in batch
    )
    system = (
        "You are a market research analyst tagging app store reviews for a "
        "quick-commerce category-discovery study. For EACH review, extract "
        "structured signals. Only use categories from this fixed list (or "
        "\"Other\" if truly none apply): " + taxonomy_list + ". "
        "Respond with strict JSON only, no prose, matching exactly this shape:\n"
        '{"results": [{'
        '"reviewId": string, '
        '"categories_mentioned": [string], '
        '"habit_signal": boolean, '
        '"habit_reason": string, '
        '"friction_point": string or null, '
        '"unmet_need": string or null, '
        '"discovery_channel": one of ["search","home_page_recommendation","banner_or_ad","word_of_mouth","browsing","notification","none_mentioned"], '
        '"segment_signal": one of ["price-sensitive","convenience-seeker","explorer","habitual","unclear"], '
        '"sentiment": one of ["positive","negative","neutral"]'
        "}]}"
    )
    user = f"Reviews to tag:\n{reviews_block}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_synthesis_prompt(aggregates: dict, sample_quotes: dict) -> list[dict]:
    """Pass B: narrate over Python-computed counts — the model may not invent numbers."""
    system = (
        "You are a product research analyst writing a report for a quick-commerce "
        "PM. You are given PRE-COMPUTED, ACCURATE counts and a set of REAL user "
        "quotes. Do not invent or alter any numbers — only use the evidence_count "
        "values you are given. Write concise, evidence-grounded analysis.\n\n"
        "Respond with strict JSON only, matching exactly this shape:\n"
        '{"top_10_categories": [{"category": string, "evidence_count": number, '
        '"rationale": string, "quotes": [string]}], '
        '"research_questions": {'
        + ", ".join(f'"{k}": {{"answer": string, "evidence_count": number}}' for k in RESEARCH_QUESTIONS)
        + "}}"
    )
    user = (
        f"Research questions to answer:\n"
        + "\n".join(f"- {k}: {v}" for k, v in RESEARCH_QUESTIONS.items())
        + f"\n\nPre-computed aggregate counts (ground truth, do not change):\n{aggregates}"
        + f"\n\nSample real quotes to draw from (attribute claims to these, do not fabricate others):\n{sample_quotes}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
