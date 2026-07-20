# Blinkit AI-Powered Discovery Engine

An automated pipeline that mines public Blinkit Play Store reviews every
night, tags them with structured signals via an LLM, and publishes
evidence-backed category recommendations to a live dashboard.

**Live dashboard:** https://pavimsc.github.io/Blinkit/
**Docs:** [problemstatement.md](problemstatement.md) (what/why) ·
[implementationPlan.md](implementationPlan.md) (build plan, traced to the
problem statement)

## Why this exists

Blinkit users tend to buy from the same few categories repeatedly. This
project mines public app reviews to answer: what's stopping people from
trying other categories, and which categories should they be nudged toward?
See [problemstatement.md](problemstatement.md) for the full brief and the
8 research questions this system answers.

## Architecture

```
 GitHub Actions (nightly cron + manual trigger)
   │
   ├─ 1. scraper/fetch_reviews.py
   │      Pulls newest Play Store reviews for com.grofers.customerapp
   │      (google-play-scraper, public data, no login) → data/raw_reviews.json
   │      Deduped by reviewId — safe to re-run.
   │
   ├─ 2. analysis/extract_themes.py   (Pass A — per review)
   │      Sends each batch of new reviews to Groq (Llama 3.1 8B) with a
   │      fixed JSON schema: which category(ies) it relates to and WHY
   │      (habitual purchase / unmet need or friction / curiosity), habit
   │      signal, friction point, unmet need, discovery channel, user
   │      segment, sentiment. → data/themes.json
   │      Uses the small/fast model here on purpose: this step runs many
   │      times a night (once per batch), and Groq's free tier gives it a
   │      500K tokens/day budget vs. 100K for the 70B model — that larger
   │      budget is saved for the one synthesis call below, where quality
   │      matters more than volume.
   │      Idempotent — only untagged reviews are sent to the model.
   │
   ├─ 3. analysis/synthesize_insights.py   (Pass B — aggregate)
   │      Python (not the LLM) counts everything: how many reviews show
   │      each category as an unmet need vs. a habitual purchase, how many
   │      show friction, etc. Python also RANKS and SELECTS the top
   │      categories from those counts. Groq (Llama 3.3 70B, one call) is
   │      only asked to write a
   │      1-2 sentence rationale per already-selected category, and to
   │      answer the 8 research questions using counts it's handed —
   │      it cannot invent a number or pick which categories appear.
   │      → data/insights.json
   │
   └─ 4. Commit data/*.json back to the repo (GITHUB_TOKEN, no extra secret)
          GitHub Pages serves dashboard/ straight off `main`, so the live
          site updates the moment the commit lands — no separate deploy step.

 dashboard/  (static HTML/CSS/JS, no build step, no framework)
   fetches ../data/insights.json client-side and renders it.
```

## Why the categories are ranked the way they are

The dashboard's "top categories to explore" list is **not** sorted by which
category is mentioned most in reviews. A category people already buy a lot
would win that contest just for being popular — which answers "what do
people already do," not "what should they try next."

Instead, each review is tagged with *why* a category came up:

- `habitual_purchase` — they already buy this regularly
- `unmet_need_or_friction` — they complain about, or wish for better
  availability/quality/service in, this category
- `curious_exploring` — first-time or occasional interest

Ranking uses only the second and third signals. Python computes this
ranking — the LLM is never asked to decide which categories make the list.

## Validation — how we know the output isn't noise

1. **Every number is traceable.** All counts on the dashboard come from
   Python aggregation over `themes.json`, not from the LLM's free-text
   output. The synthesis step explicitly overwrites any evidence count the
   model returns with the real computed value before saving.
2. **Every claim ships with real quotes.** Category rationales and research
   answers are backed by verbatim excerpts from actual reviews, visible on
   the dashboard.
3. **Manual spot-check.** `validation/spot_check.py` draws a random sample
   of already-tagged reviews into a CSV; you hand-tag them yourself (without
   looking at the model's tags), then the script scores agreement between
   your tags and the model's. Results (category agreement %, sentiment
   agreement %, overall agreement %) are written into `data/insights.json`
   and shown on the dashboard. Run it locally:
   ```
   python validation/spot_check.py sample   # writes validation/spot_check_sample.csv
   # ... fill in the human_categories / human_sentiment columns ...
   python validation/spot_check.py score    # scores it, updates the dashboard
   ```
4. **Sample size is shown, not hidden.** The dashboard flags results as
   low-confidence below 50 tagged reviews. Because `themes.json` accumulates
   every night rather than resetting, the top-category list's stability
   across nights is itself evidence the method isn't just noise.

## Known limitations (v1)

- **Play Store only.** Blinkit's iOS presence is region-inconsistent;
  App Store scraping is a documented next step, not built yet.
- **English-only reviews**, to keep LLM tagging reliable.
- **Some research questions have thin evidence.** e.g. "how do users
  discover products" rarely comes up explicitly in app reviews — the
  dashboard reports that honestly (a low/zero evidence count) rather than
  fabricating an answer.
- **Aggregate, not personalized.** This recommends categories at the
  user-base level, not per individual user.

## Repo layout

```
scraper/fetch_reviews.py        Pass 0 — pull reviews
analysis/
  prompts.py                    fixed taxonomy + prompt templates
  extract_themes.py             Pass A — per-review tagging
  synthesize_insights.py        Pass B — Python ranking + LLM rationale
  io_utils.py                   shared JSON load/save + paths
validation/spot_check.py        human-vs-LLM agreement check
dashboard/                      static site (index.html, app.js, style.css)
data/                           raw_reviews.json, themes.json, insights.json
.github/workflows/nightly.yml   cron + manual trigger automation
```

## Cost

$0. `google-play-scraper` needs no key. Groq's free tier needs no card.
GitHub Actions and GitHub Pages are free for public repos.

## Running it yourself

Requires Python 3.11+ and a `GROQ_API_KEY` environment variable (get one
free at [console.groq.com](https://console.groq.com)).

```
pip install -r requirements.txt
python scraper/fetch_reviews.py
python analysis/extract_themes.py
python analysis/synthesize_insights.py
```

`data/insights.json` is what the dashboard reads — open `dashboard/index.html`
via any local static server (not `file://`, since the browser blocks the
`fetch()` call) to preview it.
