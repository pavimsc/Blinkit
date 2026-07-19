# Problem Statement: AI-Powered Category Discovery Engine for Blinkit

## Background

Blinkit is a quick-commerce platform where users tend to form narrow, habitual
purchase patterns — repeatedly ordering from a small set of categories
(primarily groceries and snacks) while leaving the rest of the catalog
(personal care, home essentials, electronics accessories, baby care,
pet supplies, etc.) largely unexplored.

App store reviews are a rich, publicly available source of unstructured
feedback where users describe their shopping habits, frustrations, and
unmet needs in their own words — including signals about *why* they don't
branch out into new categories.

## Problem

Blinkit currently has no systematic way to mine this public review data to
understand **cross-category discovery behavior** — what drives repeat
purchases in the same categories, what blocks exploration, and which new
categories users are implicitly asking for.

## Goal

Build an automated AI "Discovery Engine" that:

1. Fetches public Blinkit reviews from the Google Play Store (and App Store,
   where available)
2. Uses an LLM (Llama 3.3 70B via the Groq API) to analyze review text for
   cross-category behavioral patterns
3. Surfaces the **top 10 categories** users should be nudged to try, backed
   by evidence from real reviews
4. Publishes results to a live, always-current dashboard
5. Re-runs automatically every night with no manual intervention

## Research Questions

The engine's output must be able to answer:

1. Why do users repeatedly buy from the same categories?
2. What prevents users from exploring new categories?
3. How do users discover products today?
4. What role do habits play in shopping behavior?
5. What information do users need before trying a new category?
6. What frustrations emerge repeatedly?
7. Which user segments are more likely to experiment?
8. What unmet needs emerge consistently across discussions?

## Success Criteria

- The dashboard is reachable via a public URL at any time (not just during a
  demo)
- Every insight and recommended category is traceable back to specific
  review excerpts (no unexplained/black-box claims)
- The nightly run requires zero manual steps once deployed
- Total running cost is effectively $0 (free-tier infra only)
- A non-technical audience (professors, classmates) can follow the
  data → analysis → insight pipeline without reading code

## Constraints

| Constraint | Detail |
|---|---|
| Budget | $0 — free APIs and free hosting tiers only |
| Timeline | Working, deployed version by tomorrow evening |
| Audience | Non-technical PM (owner) and professors (reviewers) |
| Data | Public review data only — no scraping of private/user-account data |

## Deliverables

1. Live dashboard URL showing top 10 recommended categories + supporting
   themes, refreshed nightly
2. Public GitHub repository containing all code (scraper, analysis
   pipeline, dashboard, automation config)
3. A documented, explainable architecture: how data is gathered, how
   themes are identified, how insights are generated, and how insight
   quality is validated

## Out of Scope (for this pass)

- Personalized, per-user recommendations (this is an aggregate/market-level
  discovery tool, not a recommender system for individual users)
- Non-English reviews (initial version filters to English to keep LLM
  analysis reliable within a tight timeline)
- Real-time/streaming updates (nightly batch is sufficient for the research
  goal)
