# Implementation Plan: Blinkit Category Discovery Engine

This plan implements [`problemstatement.md`](./problemstatement.md) directly.
Each section below states which line(s) of the problem statement it satisfies.

## 1. Traceability: Goal → Component

| Goal (problemstatement.md §Goal) | Implemented by |
|---|---|
| 1. Fetch public Play Store reviews | `scraper/fetch_reviews.py` |
| 2. LLM analysis for cross-category patterns | `analysis/extract_themes.py` + `analysis/synthesize_insights.py` (Groq / Llama 3.3 70B) |
| 3. Top 10 categories, evidence-backed | `synthesize_insights.py` output → `data/insights.json` |
| 4. Live, always-current dashboard | `dashboard/` static site on GitHub Pages, reads `data/insights.json` |
| 5. Nightly, zero-manual-intervention run | `.github/workflows/nightly.yml` (cron) |

## 2. Repo layout

```
Blinkit/
├── problemstatement.md
├── implementationPlan.md        (this file)
├── README.md                    architecture explainer for professors
├── requirements.txt
├── scraper/
│   └── fetch_reviews.py
├── analysis/
│   ├── prompts.py                fixed extraction schema + prompt templates
│   ├── extract_themes.py         Pass A — per-review structured tagging
│   └── synthesize_insights.py    Pass B — aggregation + narrative synthesis
├── data/
│   ├── raw_reviews.json          accumulated reviews, deduped by review id
│   ├── themes.json               per-review structured tags (append-only)
│   └── insights.json             final output the dashboard reads
├── validation/
│   └── spot_check.py             samples reviews for manual-vs-LLM agreement check
├── dashboard/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── .github/workflows/nightly.yml
```

## 3. Data source

- Platform: Google Play Store only for this pass (see §7, Out of Scope carried
  forward from problemstatement.md — App Store noted as future work since
  Blinkit's iOS presence is region-inconsistent and would add a second scraper
  under a tight deadline)
- App ID: `com.grofers.customerapp` (Blinkit's live consumer app, legacy
  package name predating the Grofers→Blinkit rebrand)
- Library: `google-play-scraper` (Python, free, no API key, public data only —
  satisfies the "public data" constraint in problemstatement.md §Constraints)
- Language filter: English only (matches Out of Scope)

## 4. Analysis pipeline (two-pass, both via Groq/Llama 3.3 70B)

**Why two passes:** keeps every number on the dashboard traceable to code,
not LLM guesswork — this directly satisfies the Success Criteria line
*"Every insight ... is traceable back to specific review excerpts."*

**Pass A — `extract_themes.py` (per review):**
For each new review, ask the model to return fixed-schema JSON:
- `categories_mentioned`: list
- `habit_signal`: bool + short reason
- `friction_point`: type + excerpt
- `unmet_need`: text or null
- `segment_signal`: e.g. price-sensitive / convenience-seeker / explorer
- `sentiment`: positive / negative / neutral

Batched ~10-15 reviews per call to control token usage. Already-processed
review IDs are skipped (idempotent), so re-running never wastes a call.

**Pass B — `synthesize_insights.py` (aggregate):**
1. Python computes counts/frequencies from all of `themes.json` (category
   mention frequency, friction-type frequency, segment distribution) —
   deterministic, not LLM-generated.
2. Those counts + a handful of representative real quotes are sent to Groq,
   which writes the narrative: the top 10 categories (with rationale) and
   answers to all 8 research questions from problemstatement.md §Research
   Questions. The LLM narrates over numbers it didn't invent — it cannot
   hallucinate a count that doesn't match the data.
3. Output written to `data/insights.json`: `{generated_at, sample_size,
   top_10_categories: [...], research_questions: {...}, validation: {...}}`

## 5. Validation (problemstatement.md §Success Criteria + your explicit ask)

| Question you asked | How the pipeline answers it |
|---|---|
| How does the workflow gather data? | §3 above — public scraper, no auth, deduped |
| How are themes identified? | Pass A fixed schema, not free-text summarization |
| How are insights generated? | Pass B — counts computed in Python, LLM only narrates |
| How is insight quality validated? | `validation/spot_check.py`: you hand-tag ~20 sampled reviews, script compares your tags to the LLM's tags on the same reviews and reports an agreement % — an inter-rater-style quality metric. Dashboard also shows current sample size and flags results as low-confidence below a threshold (e.g. <50 reviews), and because `themes.json` accumulates nightly, the top-10 list's stability over successive nights is itself evidence the method isn't noise. |

## 6. Automation (problemstatement.md §Goal, item 5)

`.github/workflows/nightly.yml`:
- `schedule` trigger (nightly cron) + `workflow_dispatch` (manual trigger, used
  for tonight's first run and for demos)
- Steps: checkout → install deps → run fetch → extract → synthesize →
  commit changed `data/*.json` using the auto-provided `GITHUB_TOKEN` (no
  extra secret beyond the `GROQ_API_KEY` you've already added) → push
- GitHub Pages serves `dashboard/` directly off `main`, so the live site
  updates the moment the commit lands — no separate deploy/build step

## 7. Deliverables checklist (problemstatement.md §Deliverables)

- [ ] Live dashboard URL (GitHub Pages) — requires you to flip the Pages
      toggle in repo Settings once `dashboard/` exists (an account-settings
      change, so that step is yours)
- [ ] Public GitHub repo with all code — already created, scraper/analysis/
      dashboard/automation to be added in this build pass
- [ ] Documented architecture — this file + `README.md`

## 8. Cost check against $0 constraint

- Scraper: free, no key
- Groq API: free tier, no card required
- GitHub Actions: free for public repos
- GitHub Pages: free
- Net cost: $0

## 9. Build order for tonight

1. `requirements.txt`, `scraper/fetch_reviews.py`
2. `analysis/prompts.py`, `extract_themes.py`, `synthesize_insights.py`
3. Run once locally/via manual workflow trigger to produce a real
   `data/insights.json`
4. `dashboard/` (reads `data/insights.json`, renders top 10 + 8 Q&As +
   validation metric)
5. `.github/workflows/nightly.yml`
6. `validation/spot_check.py`
7. `README.md` architecture write-up
8. You flip on GitHub Pages; confirm live URL works
