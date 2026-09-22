# Agentic Commerce

Multi-agent product discovery and ranking system that scrapes live data from Amazon.in and Flipkart, analyzes review authenticity, matches specifications, and produces a scored Top 10 ranking with explanations.

The system takes a product name, budget, and specs as input, then runs five specialized agents in sequence to collect, validate, and rank products based on seven weighted scoring factors.

## Architecture

```
User Input (product, budget, specs)
        |
        v
+-------------------+     Groq LLaMA 3.1 8B
|  Agent 1: Profiler | --> Extracts category, product type, budget,
+-------------------+     mandatory/preferred specs, search keywords
        |
        v
+-------------------+     ScraperAPI + BeautifulSoup + Playwright
|  Agent 2: Scraper  | --> Concurrent Amazon.in + Flipkart scraping
+-------------------+     with 3-layer fallback per platform
        |
        v
+-------------------+     SQLite price history + batch median
|  Agent 3: Historian| --> Adds 30-day price context or relative
+-------------------+     market comparison for each product
        |
        v
+-------------------+     5 heuristic signals + selective LLM
|  Agent 4: Detective| --> Detects fake reviews using rating/price
+-------------------+     anomalies, volume patterns, cross-platform gaps
        |
        v
+-------------------+     Keyword filter -> LLM spec match -> 7-factor scoring
|  Agent 5: Evaluator| --> Hard vetoes, weighted ranking, score breakdown,
+-------------------+     human-readable reasons per product
        |
        v
  Streamlit Dashboard
  (ranked results with score details)
```

## Scoring Model

Each product gets a final score from 0 to 100 based on seven normalized components:

```
final_score = spec * w1 + price * w2 + rating * w3 + popularity * w4
            + price_history * w5 + seller * w6 + trust * w7
```

Weights are category-dependent. Electronics prioritizes spec match (25%), fashion prioritizes ratings (30%), consumables prioritizes trust (30%).

| Component | What It Measures |
|---|---|
| Spec Score | How well the product satisfies mandatory and preferred requirements |
| Price Score | Budget fit using a sweet-spot curve centered around practical buying behavior |
| Rating Score | Bayesian-adjusted rating so low-review 5-star items are not overtrusted |
| Popularity Score | Log-normalized review count within the candidate batch |
| Price History Score | Historical or market-relative price attractiveness |
| Seller Score | Platform verification and seller reliability signals |
| Trust Score | Review authenticity based on Detective heuristic + LLM analysis |

### Hard Veto Rules

Products are removed entirely before scoring if they meet any of these conditions:

- Wrong product category or brand mismatch
- Accessory result when the user asked for the main product (e.g., a phone case when the query was for a phone)
- Clear contradiction of mandatory specs
- Price more than 50% above budget
- Price unrealistically below budget (likely wrong product)
- Missing price data
- Fewer than 10 reviews

This prevents a pure weighted score from accidentally promoting cheap but irrelevant products.

### Category Weight Profiles

| Category | Highest Weight | Lowest Weight |
|---|---|---|
| Electronics | Spec (25%) | Seller (5%) |
| Fashion | Rating (30%) | Spec (5%) |
| Appliances | Spec (20%) | Trust (10%) |
| Consumables | Trust (30%) | Price History (2%) |
| Furniture | Rating (25%) | Price History (3%) |

## Scraping Strategy

Each platform uses a 3-layer fallback:

```
Layer 1: ScraperAPI (proxy-backed HTML)
    |
    v (if ScraperAPI fails or returns < 3 results)
Layer 2: Direct HTTP + BeautifulSoup parsing
    |
    v (if direct HTTP fails)
Layer 3: Playwright headless browser with stealth plugins
```

- Amazon and Flipkart scrapers run concurrently using `asyncio.gather`
- If a live scrape returns fewer than 5 products for a platform, the system loads the most recent backup JSON for that query
- Successful scrapes with 10+ products per platform are saved as backups for future fallback

## Fake Review Detection

The Detective agent uses five independent heuristic signals, each contributing a weighted suspicion score:

| Signal | Weight | What It Detects |
|---|---|---|
| Rating-Volume Mismatch | 25% | High ratings with suspiciously few reviews |
| Price-Rating Anomaly | 30% | Premium products with statistically improbable perfect scores |
| Review Velocity | 15% | Sudden review count spikes suggesting coordinated campaigns |
| Cross-Platform Gap | 20% | Same product rated very differently on Amazon vs Flipkart |
| LLM Review Analysis | 10% | Semantic check on review summaries for products that cross the suspicion threshold |

Products with high suspicion get their final score capped at 40/100, regardless of other factors.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Groq API with LLaMA 3.1 8B Instant |
| Agent Framework | LangChain, LangGraph |
| Scraping | ScraperAPI, Requests, BeautifulSoup4, Playwright with Stealth |
| Data Validation | Pydantic |
| Storage | SQLite (price history), JSON (query cache, evaluator cache, backups) |
| Evaluation | Custom ranking metrics (Precision@K, NDCG, budget compliance) |

## Project Structure

```
app.py                           Streamlit frontend and pipeline orchestration
start.bat                        Windows launcher

agents/
  profiler.py                    LLM-based intent extraction to structured JSON
  scraper.py                     Concurrent scraping, deduplication, backup fallback
  historian.py                   Price history enrichment with SQLite + market median
  detective.py                   5-signal review trust scoring with LLM fallback
  evaluator.py                   3-stage evaluation: keyword filter, LLM spec match, scoring
  graph.py                       LangGraph entry point for non-UI pipeline execution

core/
  scoring.py                     7-factor scoring model, category weights, veto rules
  schemas.py                     Pydantic models for pipeline data
  validation.py                  Runtime validation helpers
  price_history.py               SQLite price observation store
  cache.py                       24-hour query result cache
  evaluator_cache.py             LLM spec-match result cache
  timing.py                      Agent latency recording and percentile stats
  eval_metrics.py                Offline ranking quality metrics
  logging_config.py              File-based logging configuration

scrapers/
  amazon_scraper.py              Amazon.in scraper (ScraperAPI + HTTP + Playwright)
  flipkart_scraper.py            Flipkart scraper (ScraperAPI + HTTP + Playwright)
  review_summary_scraper.py      Optional review summary extraction
  _utils.py                      Shared selector helpers and JSON extraction

scripts/
  evaluate_rankings.py           Offline evaluation runner

eval/
  ground_truth.example.json      Example relevance labels for ranking evaluation

data/
  sample_bluetooth_speaker_results.json   Sample output for reference
```

## Setup

### Prerequisites

- Python 3.10 or higher
- pip
- A free Groq API key from [console.groq.com](https://console.groq.com)
- (Optional) A ScraperAPI key from [scraperapi.com](https://www.scraperapi.com) for proxy-backed scraping

### Step 1: Clone and enter the project

```bash
git clone https://github.com/Shudhanshu-Khare/Agentic-commerce.git
cd Agentic-commerce
```

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install the Playwright browser

Playwright needs Chromium for browser-based scraping fallback:

```bash
playwright install chromium
```

This downloads Chromium once (~150 MB). You only need to run this the first time.

### Step 5: Set up environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
SCRAPER_API_KEY=your_scraperapi_key_here
```

`GROQ_API_KEY` is required. It powers all LLM calls (profiler, spec matching, review analysis).

`SCRAPER_API_KEY` is optional but recommended. Without it, the scraper uses direct HTTP requests and Playwright, which are more likely to be blocked by anti-bot systems.

### Step 6: Run

```bash
streamlit run app.py
```

Or on Windows, double-click `start.bat`.

The terminal will display the pipeline progress. Open the URL shown (usually `http://localhost:8501`) in your browser.

## Example Output

```
========================================
  AGENT 1 | PROFILER
========================================
   Category : electronics
   Product  : bluetooth speaker
   Budget   : Rs 3,000
   Keywords : 20 watt portable
   Duration : 1.8s

========================================
  AGENT 2 | SCRAPER
========================================
   Search : "bluetooth speaker 20 watt portable"
   Amazon.in    [OK]   18 products
   Flipkart     [OK]   12 products

========================================
  AGENT 3 | HISTORIAN
========================================
   Market Median : Rs 1,899.0

========================================
  AGENT 4 | DETECTIVE
========================================
   Scanning 24 products for review manipulation...
   Results : Authentic: 22, Suspicious: 2

========================================
  AGENT 5 | EVALUATOR
========================================
   Stage 1 - Keyword Filter  : 15 passed, 9 vetoed
   Stage 2 - AI Spec Match   : 14 passed, 1 vetoed
   Stage 3 - Scoring         : 14 products scored

========================================
  COMPLETE | 10 results in 38.5s
========================================
```

## Offline Evaluation

Run ranking quality checks against a ground-truth file:

```bash
python scripts/evaluate_rankings.py --results data/your_results.json --truth eval/ground_truth.example.json
```

Reported metrics:

| Metric | Description |
|---|---|
| Precision@K | Fraction of top-K results that are relevant |
| NDCG@10 | Normalized discounted cumulative gain |
| Budget Compliance | Percentage of results within the stated budget |
| Score Monotonicity | Whether higher-ranked products consistently have higher scores |
| Verdict Distribution | Breakdown of Authentic / Suspicious / Highly Suspicious |

## Caching and Performance

- Query results are cached for 24 hours in `data/query_cache.json` to avoid redundant scraping
- Evaluator LLM spec-match decisions are cached separately in `data/evaluator_llm_cache.json`
- Price observations are stored in SQLite (`data/price_history.db`) and accumulate across runs for historical context
- Evaluator LLM batching groups multiple products into single API calls to reduce Groq usage
- Scrape backups are saved as JSON so partial live scrapes can be repaired from recent data

## Notes

- Live scraping results vary because marketplace HTML and anti-bot behavior change frequently.
- `.env`, caches, SQLite databases, logs, backups, and virtual environments are all gitignored.
- LLMs are used only where semantic understanding is required: intent extraction, spec interpretation, and review analysis. All ranking decisions are deterministic and explainable.