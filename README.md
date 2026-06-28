# Agentic Commerce

Agentic Commerce is a multi-agent product discovery system for Amazon.in and Flipkart. A user enters a product, budget, and required specs; the app scrapes live marketplace data, checks product fit and review trust, then returns a ranked Top 10 with score breakdowns and human-readable reasons.

The goal was not to build another keyword search page. I wanted the system to behave more like a careful shopping analyst: understand the request, collect candidates from multiple sources, reject bad matches, account for trust signals, and explain why one product is better than another.

## Highlights

- Five-agent pipeline: Profiler, Scraper, Historian, Detective, and Evaluator.
- Live Amazon.in and Flipkart collection using ScraperAPI, direct HTTP parsing, and Playwright fallbacks.
- LLM-backed intent parsing and specification matching with Groq/LLaMA.
- Hard veto rules for wrong category, failed mandatory specs, unsafe budget mismatch, and weak review evidence.
- Seven-factor scoring model covering price, specs, rating, popularity, seller trust, review trust, and price history.
- Local query caching and evaluator LLM-result caching to reduce repeat latency and API usage.
- SQLite price observations for historical context across repeated runs.
- Streamlit dashboard with per-agent progress, timings, score details, and ranking explanations.
- Offline evaluation script for ranking metrics such as Precision@K, NDCG, budget compliance, and monotonicity.

## How It Works

```text
User request
   |
   v
Agent 1: Profiler
   Converts natural language into a validated shopping profile.
   Example: category, product type, budget, mandatory specs, preferred specs.
   |
   v
Agent 2: Scraper
   Collects Amazon.in and Flipkart candidates with layered fallbacks.
   Deduplicates near-identical products across platforms.
   |
   v
Agent 3: Historian
   Adds market-price context from SQLite history when available,
   otherwise falls back to batch-relative price comparison.
   |
   v
Agent 4: Detective
   Scores review trust using metadata heuristics plus batched LLM analysis
   for suspicious products.
   |
   v
Agent 5: Evaluator
   Applies keyword prefiltering, AI spec matching, scoring, hard vetoes,
   and final Top 10 ranking.
```

## Agents

| Agent | Role | Key Design Choice |
| --- | --- | --- |
| Profiler | Parses the user's request into structured JSON | Uses Groq/LLaMA with validation and fallback parsing |
| Scraper | Collects product candidates | Runs Amazon and Flipkart concurrently, then repairs partial data from backups when possible |
| Historian | Adds price context | Uses SQLite price history first, relative market median second |
| Detective | Estimates review authenticity | Combines deterministic metadata signals with selective LLM checks |
| Evaluator | Produces the final ranking | Uses hard vetoes before scoring so irrelevant products do not survive just because they are cheap or popular |

## Ranking Model

Each product receives normalized component scores and then a weighted final score from 0 to 100.

```text
final_score =
    spec_weight          * spec_score
  + price_weight         * price_score
  + rating_weight        * rating_score
  + popularity_weight    * popularity_score
  + price_history_weight * price_history_score
  + seller_weight        * seller_score
  + trust_weight         * trust_score
```

The weights change by category. For example, electronics gives more importance to specs, while consumables and fashion give more importance to trust and ratings.

### Score Components

| Component | What It Measures |
| --- | --- |
| `spec_score` | How well the title/specs satisfy mandatory and preferred requirements |
| `price_score` | Budget fit using a sweet-spot curve around practical buying behavior |
| `rating_score` | Bayesian rating score so low-review 5-star items are not overtrusted |
| `popularity_score` | Log-normalized review count within the candidate batch |
| `price_history_score` | Historical or market-relative price attractiveness |
| `seller_score` | Platform and seller reliability |
| `trust_score` | Review authenticity based on Detective signals |

## Hard Veto Rules

The system deliberately removes products that should not compete in the final ranking:

- Wrong product category or brand mismatch.
- Accessory result when the user asked for the main product.
- Clear contradiction of mandatory specs.
- Price more than 50% above budget.
- Price unrealistically below budget, which often indicates a wrong product.
- Missing price data.
- Fewer than 10 reviews.
- Very low review-trust score, which caps the final score.

This is important because a pure weighted score can accidentally reward cheap but irrelevant products. The veto layer keeps the ranking aligned with the user's actual intent.

## Reliability and Performance

- Query results are cached for 24 hours in `data/query_cache.json`.
- Evaluator LLM decisions are cached separately in `data/evaluator_llm_cache.json`.
- Scraping uses multiple layers: ScraperAPI, direct HTTP with BeautifulSoup, and Playwright as a browser fallback.
- Scrape backups are stored as JSON so a partial live scrape can still be repaired.
- Evaluator LLM spec matching is batched to reduce API calls.
- Groq evaluator batches run sequentially to avoid free-tier rate-limit retries.
- Agent timings are recorded and shown in the Streamlit UI.

## Tech Stack

| Area | Tools |
| --- | --- |
| UI | Streamlit |
| Agent orchestration | LangGraph, manual progress-aware Streamlit pipeline |
| LLM | Groq API with LLaMA 3.1 |
| Scraping | ScraperAPI, requests, BeautifulSoup, Playwright |
| Validation | Pydantic |
| Storage | SQLite, local JSON cache |
| Evaluation | Custom Python metrics for ranking quality |

## Project Structure

```text
app.py                         Streamlit app and progress-aware pipeline
start.bat                      Windows launcher for the Streamlit app
clean.bat                      Local cleanup helper

agents/
  profiler.py                  Intent extraction
  scraper.py                   Scrape orchestration, backup loading, deduplication
  historian.py                 Price-history and market-median enrichment
  detective.py                 Review trust and suspicious-pattern detection
  evaluator.py                 Spec matching, scoring, vetoes, and ranking
  graph.py                     LangGraph entry point for non-UI usage

core/
  scoring.py                   Score components, category weights, final ranking logic
  schemas.py                   Pydantic models
  validation.py                Runtime validation helpers
  price_history.py             SQLite price observation store
  cache.py                     Query result cache
  evaluator_cache.py           LLM spec-match cache
  timing.py                    Agent latency logging
  eval_metrics.py              Offline ranking metrics
  logging_config.py            File logging setup

scrapers/
  amazon_scraper.py            Amazon.in scraper with layered fallbacks
  flipkart_scraper.py          Flipkart scraper with query variants and fallbacks
  review_summary_scraper.py    Optional deeper review-summary extraction module

scripts/
  evaluate_rankings.py         Offline evaluation runner

eval/
  ground_truth.example.json    Example relevance labels for evaluation

data/
  *.json                       Saved scrape backups and sample result data
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
playwright install chromium
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key
SCRAPER_API_KEY=your_scraperapi_key
```

`SCRAPER_API_KEY` is optional, but recommended. Without it, the scraper falls back to direct HTTP and Playwright.

## Running the App

On Windows:

```powershell
.\start
```

Or run Streamlit directly:

```powershell
streamlit run app.py
```

Once Streamlit starts, open the local URL shown in the terminal, usually:

```text
http://localhost:8501
```

## Example Terminal Flow

```text
AGENT 1 - PROFILER
   Category : electronics
   Product  : smartwatch
   Budget   : Rs 2,000
   Keywords : noise black
   Time     : 1.3s

AGENT 2 - SCRAPER
   Search : "smartwatch noise black"
   Amazon.in    22 products
   Flipkart     0 products

AGENT 3 - HISTORIAN
   Market Median : Rs 1,499.0

AGENT 4 - DETECTIVE
   Scanning products for review manipulation...
   Results: Authentic / Suspicious / Highly Suspicious

AGENT 5 - EVALUATOR
   Stage 1 - Keyword Filter
   Stage 2 - AI Spec Match
   Stage 3 - Scoring

PIPELINE COMPLETE
```

## Offline Evaluation

Run ranking checks against a saved result JSON:

```powershell
python scripts\evaluate_rankings.py --results data\your_results.json --truth eval\ground_truth.example.json
```

The evaluator reports metrics such as:

- Precision@K
- NDCG@10
- Budget compliance
- Score monotonicity
- Verdict distribution

## Why This Is Not A Chatbot

- Unlike chatbot shopping assistants, Agentic Commerce uses a
deterministic ranking pipeline with hard constraints and explicit
tradeoffs.
- LLMs are used only where semantic understanding is required:
intent extraction, specification interpretation, and suspicious
review reasoning.
- Final ranking decisions remain explainable and reproducible.

## Notes

- Live scraping can vary because marketplace pages and anti-bot behavior change often.
- `.env`, local caches, SQLite databases, logs, and virtual environments are ignored by git.
- The app is built as a product intelligence project, not as checkout automation.