# 🛒 Agentic Commerce — Complete Project Blueprint
### AI-Powered Product Discovery & Ranking for Indian E-Commerce
> **Stack:** LangChain / LangGraph · Groq API (Free LLM) · Playwright · Streamlit · MongoDB Atlas  
> **Platforms:** Amazon.in · Flipkart (40–50 products total)  
> **Category:** Generalized — Electronics, Tech, Fashion, Appliances & more  
> **💸 Total Cost: ₹0 — 100% Free to build and run**

---

## 📌 Table of Contents
1. [What You're Building](#1-what-youre-building)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack & Tools](#3-tech-stack--tools)
4. [Project Folder Structure](#4-project-folder-structure)
5. [Environment Setup](#5-environment-setup)
6. [Phase 1 — Intent Parser Agent](#6-phase-1--intent-parser-agent)
7. [Phase 2 — Data Collector Agents](#7-phase-2--data-collector-agents)
8. [Phase 3 — Price History Agent](#8-phase-3--price-history-agent)
9. [Phase 4 — Review Trust Agent](#9-phase-4--review-trust-agent)
10. [Phase 5 — Scoring & Ranking Engine](#10-phase-5--scoring--ranking-engine)
11. [Phase 6 — LangGraph Orchestration](#11-phase-6--langgraph-orchestration)
12. [Phase 7 — Streamlit UI](#12-phase-7--streamlit-ui)
13. [The Ranking Formula (Full Math)](#13-the-ranking-formula-full-math)
14. [Dynamic Weights by Category](#14-dynamic-weights-by-category)
15. [How to Run the Project](#15-how-to-run-the-project)
16. [API Keys & Costs](#16-api-keys--costs)
17. [Common Pitfalls & Fixes](#17-common-pitfalls--fixes)
18. [Roadmap & Advanced Features](#18-roadmap--advanced-features)

---

## ⚡ 3-Day Build Plan (Demo-Ready)

> Stick to this order. Don't skip ahead. Each day ends with something you can actually run.

### 🗓️ Day 1 — The Spine
**Goal:** User types a query → system finds real products → you can print them in terminal

| Time | Task |
|------|------|
| Morning | Set up project folder, venv, install all packages, get Groq API key |
| Afternoon | Build Agent 1 (Profiler) — test with 5 different queries |
| Evening | Build Agent 2 (Scraper) with Playwright — Amazon.in first, then Flipkart |
| Night | Wire both together, print 40 products to terminal ✅ |

**Day 1 checkpoint:** `python core/graph.py` prints 40 real products from both platforms.

### 🗓️ Day 2 — The Brain
**Goal:** Products get scored, fake reviews get detected, ranking works

| Time | Task |
|------|------|
| Morning | Build Agent 4 (Detective) — all 9 fake review signals |
| Afternoon | Build Agent 5 (Evaluator) — scoring formula + dynamic weights per category |
| Evening | Wire into LangGraph pipeline — full pipeline runs end to end |
| Night | Test with 3 different product types (laptop, phone, shoes) ✅ |

**Day 2 checkpoint:** `python core/graph.py` returns Top 10 ranked products with scores out of 100.

### 🗓️ Day 3 — The Face
**Goal:** Looks impressive, demo-ready, professor-worthy

| Time | Task |
|------|------|
| Morning | Build Streamlit UI — search bar, results, score cards |
| Afternoon | Add score breakdown bars, fake review warnings, "Why this?" section |
| Evening | Polish UI, test 10 different queries across categories |
| Night | Rehearse demo flow, write README ✅ |

**Day 3 checkpoint:** Full working demo you can present confidently to your professor.

> **Skip for now** (add in Phase 2): Price history agent, real per-product review scraping, MongoDB caching. Your 3-day build will be impressive without them.

---

## 1. What You're Building

**Agentic Commerce** is an AI system where a user types a natural language product request like:

> *"I want a gaming laptop under ₹80,000 with RTX GPU and good battery life"*

…and the system automatically:
- Parses the intent into structured data
- Searches Amazon.in and Flipkart in parallel (40–50 products total)
- Fetches price history to check if it's a real deal
- Detects fake reviews using 9 signals including location clustering, duplicate text detection, and platform AI summaries
- Runs a custom scoring formula per product category
- Returns the **Top 5–10 ranked products** with explanations

**This is NOT a simple search engine. It's an autonomous multi-agent pipeline.**

---

## 2. System Architecture

```
User Input (Natural Language)
        │
        ▼
┌─────────────────────┐
│   Agent 1: Profiler  │  → Converts text → structured JSON
│   (LangChain LLM)   │    {category, budget, specs, constraints}
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│  Agent 2: Scraper   │  → Hits Amazon.in & Flipkart in parallel
│  (SerpApi / Bright  │    ~25 products per platform = 40–50 total
│   Data / Playwright)│
└─────────────────────┘
        │
        ▼
┌──────────────────────┐
│  Agent 3: Historian  │  → Fetches 90-day price history
│  (Keepa API /        │    Flags if current price is inflated
│   PriceHistory.in)   │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  Agent 4: Detective  │  → Scrapes top reviews
│  (LLM + Heuristics)  │    Detects fake reviews
│                      │    Computes "True Rating"
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  Agent 5: Evaluator  │  → Runs scoring formula
│  (Custom Python)     │    Ranks all products
│                      │    Generates "Why this?" explanation
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│   Streamlit UI       │  → Displays Top 5–10 with scores,
│                      │    comparisons, warnings, charts
└──────────────────────┘
```

**Orchestration:** All agents are connected using **LangGraph** (a LangChain extension for building stateful agent pipelines with nodes and edges).

---

## 3. Tech Stack & Tools

| Layer | Tool | Cost | Purpose |
|-------|------|------|---------|
| **LLM** | `Groq API` (llama-3.1-8b-instant) | ✅ Free | Intent parsing, fake review detection, spec matching, summaries |
| **Agent Framework** | `LangGraph` + `LangChain` | ✅ Free | Orchestrating the multi-agent pipeline |
| **Scraping** | `Playwright` + `BeautifulSoup` | ✅ Free | Direct scraping of Amazon.in & Flipkart |
| **Price History** | Skipped in 3-day build | ✅ Free | Add later with Keepa free tier |
| **Database** | `MongoDB Atlas` free tier | ✅ Free | 512MB — more than enough |
| **Frontend** | `Streamlit` | ✅ Free | Clean, fast UI — no React needed |
| **Environment** | `python-dotenv` | ✅ Free | Managing API keys |
| **Package Mgmt** | `pip` + `requirements.txt` | ✅ Free | Standard Python |

### Why Groq instead of OpenAI?
Groq gives you a **completely free API key** — no credit card, no billing. It runs open-source models (Llama 3.1) that are more than good enough for this project. It's also extremely fast — much faster than OpenAI in many cases. Sign up at **console.groq.com** and grab your free key in 2 minutes.

---

## 4. Project Folder Structure

```
agentic-commerce/
│
├── agents/
│   ├── __init__.py
│   ├── profiler.py          # Agent 1: Intent Parser
│   ├── scraper.py           # Agent 2: Data Collector
│   ├── historian.py         # Agent 3: Price History
│   ├── detective.py         # Agent 4: Fake Review Detector
│   └── evaluator.py         # Agent 5: Scorer & Ranker
│
├── core/
│   ├── __init__.py
│   ├── graph.py             # LangGraph pipeline orchestration
│   ├── schemas.py           # Pydantic models (data shapes)
│   ├── scoring.py           # Ranking formula logic
│   └── weights.py           # Dynamic weights per category
│
├── scrapers/
│   ├── __init__.py
│   ├── amazon_scraper.py    # Amazon.in scraper
│   ├── flipkart_scraper.py  # Flipkart scraper
│   └── review_summary_scraper.py  # Platform AI summary scraper
│
├── db/
│   ├── __init__.py
│   └── mongo.py             # MongoDB connection & helpers
│
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI app (optional, for production)
│
├── ui/
│   └── app.py               # Streamlit frontend
│
├── .env                     # API keys (never commit this)
├── requirements.txt
└── README.md
```

---

## 5. Environment Setup

### Step 1 — Create project & virtual environment

```bash
mkdir agentic-commerce
cd agentic-commerce
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### Step 2 — Install all dependencies

```bash
pip install langchain langgraph langchain-groq langchain-community
pip install groq
pip install streamlit
pip install pymongo
pip install requests beautifulsoup4 playwright
pip install python-dotenv pydantic
pip install pandas numpy
pip install difflib
```

```
# requirements.txt
langchain==0.2.16
langgraph==0.2.28
langchain-groq==0.1.9
groq==0.9.0
streamlit==1.37.0
pymongo==4.8.0
requests==2.32.3
beautifulsoup4==4.12.3
playwright==1.46.0
python-dotenv==1.0.1
pydantic==2.8.2
pandas==2.2.2
numpy==2.0.1
```

### Step 3 — Set up `.env` file

```env
# Get this FREE at console.groq.com — no credit card needed
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# MongoDB Atlas free tier — mongodb.com/atlas
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
```

> 🔑 **Getting your free Groq key:**
> 1. Go to [console.groq.com](https://console.groq.com)
> 2. Sign up with Google (2 minutes)
> 3. Click "Create API Key"
> 4. Done — free, no card, generous limits

---

## 6. Phase 1 — Intent Parser Agent

**File:** `agents/profiler.py`

**What it does:** Takes the user's raw text and converts it into a clean, structured JSON using an LLM.

### The Prompt Design

```python
PROFILER_PROMPT = """
You are an expert product specification extractor for Indian e-commerce.

Given the user's input, extract the following into a strict JSON format:

{{
  "category": "<electronics|fashion|appliances|consumables|furniture|other>",
  "product_type": "<specific type e.g. laptop, phone, shoes>",
  "budget_inr": <integer in rupees, null if not mentioned>,
  "budget_flexibility": <0.10 means 10% above budget is okay>,
  "mandatory_specs": {{
    "<spec_name>": "<value>"
  }},
  "preferred_specs": {{
    "<spec_name>": "<value>"
  }},
  "constraints": ["new only", "trusted seller", etc.],
  "use_case": "<gaming, office work, fitness, etc.>"
}}

Rules:
- Convert "under 80k" → budget_inr: 80000
- Convert "RTX GPU" → mandatory_specs: {{"gpu": "RTX"}}
- If user says "good battery", add to preferred_specs: {{"battery": "good"}}
- Category MUST be one of the listed options.
- Return ONLY valid JSON. No explanation. No markdown.

User Input: {user_input}
"""
```

### The Agent Code

```python
# agents/profiler.py

import json
import os
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

PROFILER_PROMPT = """
You are an expert product specification extractor for Indian e-commerce.
Given the user's input, extract the following into strict JSON.
Handle ALL product categories — electronics, fashion, appliances, consumables, furniture, and more.

{{
  "category": "<electronics|fashion|appliances|consumables|furniture|other>",
  "product_type": "<laptop, phone, shoes, mixer, etc.>",
  "budget_inr": <integer or null>,
  "budget_flexibility": 0.10,
  "mandatory_specs": {{}},
  "preferred_specs": {{}},
  "constraints": [],
  "use_case": "<gaming, office, fitness, cooking, etc.>"
}}

Category rules:
- electronics: phones, laptops, tablets, cameras, headphones, TVs
- fashion: clothes, shoes, bags, watches, jewelry
- appliances: washing machine, refrigerator, AC, mixer, microwave
- consumables: food, skincare, medicines, supplements
- furniture: chairs, tables, beds, sofas
- other: anything else

Return ONLY valid JSON. No markdown. No explanation.
User Input: {user_input}
"""

def run_profiler(user_input: str) -> dict:
    llm = ChatGroq(
        model="llama-3.1-8b-instant",   # free, fast
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    prompt = PromptTemplate(
        input_variables=["user_input"],
        template=PROFILER_PROMPT
    )

    chain = prompt | llm
    response = chain.invoke({"user_input": user_input})

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


if __name__ == "__main__":
    tests = [
        "gaming laptop under 80000 with RTX GPU",
        "Nike running shoes under 5000",
        "Samsung 1.5 ton 5 star AC",
        "wireless earbuds with noise cancellation under 3000",
        "office chair under 15000 with lumbar support"
    ]
    for t in tests:
        print(f"\nInput: {t}")
        print(json.dumps(run_profiler(t), indent=2))
```

**Expected Output:**
```json
{
  "category": "electronics",
  "product_type": "laptop",
  "budget_inr": 80000,
  "budget_flexibility": 0.10,
  "mandatory_specs": {
    "gpu": "RTX"
  },
  "preferred_specs": {
    "battery": "long battery life",
    "use_case": "gaming"
  },
  "constraints": ["new only"],
  "use_case": "gaming"
}
```

---

## 7. Phase 2 — Data Collector Agents

**File:** `agents/scraper.py`

**100% free** — uses Playwright to directly scrape Amazon.in and Flipkart in parallel. No SerpApi, no paid APIs.

```python
# agents/scraper.py

import asyncio
import re
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor

# ─── Amazon.in Scraper ──────────────────────────────────────────

async def scrape_amazon(query: str, max_results: int = 25) -> list[dict]:
    products = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            locale="en-IN",
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"}
        )
        page = await context.new_page()

        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}&ref=sr_pg_1"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[Amazon] Page load failed: {e}")
            await browser.close()
            return []

        items = await page.query_selector_all('[data-component-type="s-search-result"]')

        for item in items[:max_results]:
            try:
                title_el   = await item.query_selector("h2 span")
                price_el   = await item.query_selector(".a-price-whole")
                rating_el  = await item.query_selector(".a-icon-alt")
                reviews_el = await item.query_selector(".a-size-base.s-underline-text")
                link_el    = await item.query_selector("h2 a")
                img_el     = await item.query_selector(".s-image")

                title   = (await title_el.inner_text()).strip()   if title_el   else ""
                price   = parse_price(await price_el.inner_text() if price_el else "0")
                rating  = parse_rating(await rating_el.inner_text() if rating_el else "0")
                reviews = parse_reviews(await reviews_el.inner_text() if reviews_el else "0")
                href    = await link_el.get_attribute("href")     if link_el    else ""
                img     = await img_el.get_attribute("src")       if img_el     else ""

                if not title or price == 0:
                    continue

                products.append({
                    "title":         title,
                    "price":         price,
                    "rating":        rating,
                    "reviews_count": reviews,
                    "seller":        "Amazon.in",
                    "url":           f"https://www.amazon.in{href}" if href.startswith("/") else href,
                    "thumbnail":     img,
                    "platform":      "Amazon.in",
                    "specs":         {}
                })
            except Exception:
                continue

        await browser.close()
    print(f"[Scraper] Amazon.in: {len(products)} products")
    return products


# ─── Flipkart Scraper ───────────────────────────────────────────

async def scrape_flipkart(query: str, max_results: int = 25) -> list[dict]:
    products = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            locale="en-IN"
        )
        page = await context.new_page()

        url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)

            # Dismiss login popup if it appears
            try:
                close_btn = await page.query_selector("button._2KpZ6l._2doB4z")
                if close_btn:
                    await close_btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass

        except Exception as e:
            print(f"[Flipkart] Page load failed: {e}")
            await browser.close()
            return []

        # Flipkart has two layouts depending on category
        # Layout A: grid cards (electronics)
        # Layout B: list cards (mixed)
        card_selectors = [
            "._1AtVbE",    # Grid layout card
            "._2kHMtA",    # List layout card
            "._4ddWXP",    # Another common wrapper
        ]

        items = []
        for selector in card_selectors:
            items = await page.query_selector_all(selector)
            if len(items) > 3:
                break

        for item in items[:max_results]:
            try:
                title_el   = await item.query_selector("._4rR01T, .s1Q9rs, .IRpwTa")
                price_el   = await item.query_selector("._30jeq3, ._1_WHN1")
                rating_el  = await item.query_selector("._3LWZlK")
                reviews_el = await item.query_selector("._2_R_DZ, ._13vcmD")
                link_el    = await item.query_selector("a._1fQZEK, a.s1Q9rs, a._2rpwqI")
                img_el     = await item.query_selector("img._396cs4, img._2r_T1I")

                title   = (await title_el.inner_text()).strip()   if title_el   else ""
                price   = parse_price(await price_el.inner_text() if price_el else "0")
                rating  = parse_rating(await rating_el.inner_text() if rating_el else "0")
                reviews = parse_reviews(await reviews_el.inner_text() if reviews_el else "0")
                href    = await link_el.get_attribute("href")     if link_el    else ""
                img     = await img_el.get_attribute("src")       if img_el     else ""

                if not title or price == 0:
                    continue

                products.append({
                    "title":         title,
                    "price":         price,
                    "rating":        rating,
                    "reviews_count": reviews,
                    "seller":        "Flipkart",
                    "url":           f"https://www.flipkart.com{href}" if href.startswith("/") else href,
                    "thumbnail":     img,
                    "platform":      "Flipkart",
                    "specs":         {}
                })
            except Exception:
                continue

        await browser.close()
    print(f"[Scraper] Flipkart: {len(products)} products")
    return products


# ─── Helpers ────────────────────────────────────────────────────

def parse_price(text: str) -> float:
    cleaned = re.sub(r'[^\d.]', '', str(text).replace(',', ''))
    try:
        return float(cleaned)
    except:
        return 0.0

def parse_rating(text: str) -> float:
    match = re.search(r'[\d.]+', str(text))
    try:
        return float(match.group()) if match else 0.0
    except:
        return 0.0

def parse_reviews(text: str) -> int:
    cleaned = re.sub(r'[^\d]', '', str(text).replace(',', '').replace('(', '').replace(')', ''))
    try:
        return int(cleaned)
    except:
        return 0


# ─── Run Both in Parallel ───────────────────────────────────────

def run_scraper(profile: dict) -> list[dict]:
    """
    Runs Amazon + Flipkart scrapers in parallel using threads.
    Each runs its own asyncio event loop.
    Returns 40–50 combined products.
    """
    query = build_search_query(profile)
    print(f"[Scraper] Query: '{query}'")

    def run_amazon():
        return asyncio.run(scrape_amazon(query, max_results=25))

    def run_flipkart():
        return asyncio.run(scrape_flipkart(query, max_results=25))

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_amazon   = executor.submit(run_amazon)
        f_flipkart = executor.submit(run_flipkart)
        amazon_results   = f_amazon.result()
        flipkart_results = f_flipkart.result()

    all_products = amazon_results + flipkart_results
    print(f"[Scraper] Total: {len(all_products)} products")
    return all_products


def build_search_query(profile: dict) -> str:
    parts = [profile.get("product_type", "")]
    for val in profile.get("mandatory_specs", {}).values():
        parts.append(str(val))
    if profile.get("budget_inr"):
        parts.append(f"under {profile['budget_inr']}")
    return " ".join(filter(None, parts))


if __name__ == "__main__":
    # Quick test
    mock_profile = {
        "product_type": "gaming laptop",
        "mandatory_specs": {"gpu": "RTX"},
        "budget_inr": 80000
    }
    products = run_scraper(mock_profile)
    for p in products[:5]:
        print(f"{p['platform']} | ₹{p['price']:,.0f} | {p['title'][:60]}")
```

> ⚠️ **Selector Note:** Flipkart and Amazon change their CSS class names occasionally. If you get 0 results, open the site in Chrome, right-click a product card → Inspect, and find the updated class name. This is normal web scraping maintenance.

---

## 8. Phase 3 — Price History Agent

**File:** `agents/historian.py`

> ⏭️ **Skip this in your 3-day build.** Focus on Day 1 and Day 2 first. Add this in Phase 2 once your core pipeline works.

**Why skipped?** Keepa API (the best source for Amazon price history) requires a paid key for serious use. For the 3-day demo, the system already handles pricing well via the Price Score (budget vs. current price comparison across 40–50 products).

### Free Alternative — Cross-Product Price Comparison

Instead of historical price tracking, we compare every product's price against the **median price of all scraped results**. This tells the user whether a product is priced high or low *relative to the current market* — which is often more useful anyway.

```python
# agents/historian.py (free version — no Keepa needed)

import statistics

def compute_relative_price_score(product: dict, all_products: list[dict]) -> float:
    """
    Compares a product's price against the median price of all scraped products
    of the same category. Returns 0–1.

    1.0 = significantly cheaper than market median (great deal)
    0.5 = at market median (fair price)
    0.0 = significantly above market median (overpriced)
    """
    prices = [p["price"] for p in all_products if p.get("price", 0) > 0]
    if len(prices) < 3:
        return 0.5  # not enough data

    median_price = statistics.median(prices)
    current = product.get("price", median_price)

    # How much cheaper is this product vs. the median?
    score = (median_price - current) / median_price
    # Clamp to [0, 1]
    return round(max(0.0, min(1.0, 0.5 + score)), 3)


def run_historian(products: list[dict]) -> list[dict]:
    """
    Enriches each product with a relative price score.
    Called in the pipeline with the full list of 40-50 products.
    """
    enriched = []
    for product in products:
        product["price_history_score"] = compute_relative_price_score(product, products)
        product["price_history"] = {
            "method": "relative_market_comparison",
            "median_market_price": round(statistics.median(
                [p["price"] for p in products if p.get("price", 0) > 0]
            ), 0),
            "current_price": product.get("price", 0)
        }
        enriched.append(product)
    return enriched
```

> 🔮 **Phase 2 upgrade:** Once the demo is done, add Keepa API (free tier: 1 request/minute) to get real 90-day price history for Amazon products. The `price_history_score` field in the schema is already there — just swap the function.

---

## 9. Phase 4 — Review Trust Agent

**File:** `agents/detective.py`

This is the most **impressive** part of your project. The system runs **9 distinct fake review signals** — a combination of heuristics, NLP, and LLM analysis — plus reads the platform's own AI-generated review summary (Amazon's "About this item" / Flipkart's "Review Highlights") as an additional trust signal.

### The 9 Fake Review Signals

| # | Signal | What It Catches |
|---|--------|----------------|
| 1 | **Unverified purchase ratio** | Reviews from non-buyers |
| 2 | **5-star distribution** | Abnormal rating concentration |
| 3 | **Short review length** | Meaningless 1-word reviews |
| 4 | **Same-day burst** | Review bombing campaigns |
| 5 | **Location clustering** | All reviews from one city/region |
| 6 | **Duplicate/near-duplicate text** | Copy-pasted fake reviews |
| 7 | **Reviewer name patterns** | Bot-like names (User12345, etc.) |
| 8 | **Platform AI summary cross-check** | Contradictions in Amazon/Flipkart's own summary |
| 9 | **LLM deep analysis** | Linguistic patterns, generic praise, robotic tone |

```python
# agents/detective.py

import os
import re
import json
from collections import Counter
from difflib import SequenceMatcher
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

# ─── LLM Prompt ─────────────────────────────────────────────────

FAKE_REVIEW_PROMPT = """
You are a fake review detection expert for Indian e-commerce platforms.

Analyze the following product reviews carefully.

Look for these RED FLAGS:
1. Generic praise with no specific product details ("Amazing product!", "Best buy ever!", "Very nice")
2. Repetitive sentence structures or near-identical phrasing across different reviews
3. No mention of any product negatives at all (real buyers always find something)
4. Unusually formal, robotic, or AI-generated language
5. Reviews that don't match the product category (e.g., a laptop review talking about fabric texture)
6. Extreme emotional language with zero substance ("BEST PRODUCT EVER OMG")
7. Reviewer seems to not have used the product (no personal experience mentioned)

Also consider this platform AI summary of all reviews:
Platform Summary: {platform_summary}

Check if the individual reviews CONTRADICT the platform summary. If reviews are mostly generic
but the platform summary mentions specific problems, that's a red flag.

Reviews to analyze:
{reviews}

Return ONLY a JSON object (no markdown, no explanation):
{{
  "llm_fake_score": <float 0.0 to 1.0>,
  "red_flags": ["list of specific issues found"],
  "platform_summary_contradiction": <true|false>,
  "verdict": "<Authentic | Suspicious | Highly Suspicious>"
}}
"""

# ─── Signal Checkers ────────────────────────────────────────────

def check_unverified_ratio(reviews: list[dict]) -> tuple[float, str | None]:
    """Signal 1: Unverified purchase ratio."""
    total = len(reviews)
    unverified = sum(1 for r in reviews if not r.get("verified", True))
    ratio = unverified / total
    if ratio > 0.35:
        return 0.20, f"{int(ratio*100)}% of reviews are from unverified purchases"
    return 0.0, None


def check_star_distribution(reviews: list[dict]) -> tuple[float, str | None]:
    """Signal 2: Suspicious 5-star concentration."""
    total = len(reviews)
    five_star = sum(1 for r in reviews if r.get("rating", 0) == 5)
    ratio = five_star / total
    if ratio > 0.88:
        return 0.15, f"{int(ratio*100)}% of reviews are 5-star — unnatural distribution"
    return 0.0, None


def check_short_reviews(reviews: list[dict]) -> tuple[float, str | None]:
    """Signal 3: Suspiciously short/empty reviews."""
    total = len(reviews)
    short = sum(1 for r in reviews if len(r.get("text", "")) < 25)
    ratio = short / total
    if ratio > 0.50:
        return 0.10, f"{int(ratio*100)}% of reviews are under 25 characters — generic/empty"
    return 0.0, None


def check_date_clustering(reviews: list[dict]) -> tuple[float, str | None]:
    """Signal 4: Review bombing — burst of reviews on same day."""
    total = len(reviews)
    dates = [r.get("date", "") for r in reviews if r.get("date")]
    if not dates:
        return 0.0, None
    date_counts = Counter(dates)
    max_same_day = max(date_counts.values())
    if max_same_day > total * 0.30:
        worst_date = date_counts.most_common(1)[0][0]
        return 0.20, f"{max_same_day} reviews posted on {worst_date} — possible review bombing"
    return 0.0, None


def check_location_clustering(reviews: list[dict]) -> tuple[float, str | None]:
    """
    Signal 5: Geographic clustering.
    Amazon/Flipkart sometimes include city in review metadata.
    If >40% of reviews come from the same city, it's suspicious.
    """
    locations = [r.get("location", "").strip().lower() for r in reviews if r.get("location", "").strip()]
    if len(locations) < 5:
        return 0.0, None  # Not enough location data to judge

    location_counts = Counter(locations)
    most_common_city, most_common_count = location_counts.most_common(1)[0]
    ratio = most_common_count / len(locations)

    if ratio > 0.40 and most_common_city not in ("india", ""):
        return 0.15, (
            f"{int(ratio*100)}% of reviews are from '{most_common_city.title()}' — "
            f"geographic clustering detected"
        )
    return 0.0, None


def check_duplicate_reviews(reviews: list[dict]) -> tuple[float, str | None]:
    """
    Signal 6: Near-duplicate review text detection.
    Uses SequenceMatcher to find reviews that are >80% similar to each other.
    """
    texts = [r.get("text", "").strip().lower() for r in reviews if len(r.get("text", "")) > 15]
    duplicate_pairs = 0

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            similarity = SequenceMatcher(None, texts[i], texts[j]).ratio()
            if similarity > 0.80:
                duplicate_pairs += 1

    if duplicate_pairs >= 3:
        return 0.20, f"{duplicate_pairs} pairs of near-identical reviews detected — copy-paste campaign likely"
    elif duplicate_pairs >= 1:
        return 0.08, f"{duplicate_pairs} near-duplicate review pair(s) found"
    return 0.0, None


def check_reviewer_name_patterns(reviews: list[dict]) -> tuple[float, str | None]:
    """
    Signal 7: Bot-like reviewer names.
    Patterns: 'User12345', 'Amazon Customer', 'A***n', random strings.
    """
    names = [r.get("reviewer_name", "") for r in reviews if r.get("reviewer_name")]
    if not names:
        return 0.0, None

    bot_pattern = re.compile(
        r'^(amazon customer|flipkart customer|user\d+|customer\d+|[a-z]{1,3}\*+[a-z]{0,3})$',
        re.IGNORECASE
    )
    bot_names = sum(1 for name in names if bot_pattern.match(name.strip()))
    ratio = bot_names / len(names)

    if ratio > 0.40:
        return 0.10, f"{int(ratio*100)}% of reviewers have anonymous/bot-pattern names"
    return 0.0, None


def check_platform_summary(
    reviews: list[dict],
    platform_summary: str
) -> tuple[float, str | None]:
    """
    Signal 8: Cross-check individual reviews against Amazon/Flipkart's
    own AI-generated review summary.

    If the platform summary mentions issues (e.g., 'some users report heating problems')
    but all individual reviews are 5-star with no negatives, that's a contradiction.
    """
    if not platform_summary or platform_summary == "Not available":
        return 0.0, None

    # Keywords that suggest the platform summary has found negatives
    negative_keywords = [
        "however", "some users", "a few customers", "reported issues",
        "complaint", "problem", "concern", "disappointing", "not satisfied",
        "could be better", "improvement needed", "heating", "battery drain"
    ]

    summary_has_negatives = any(kw in platform_summary.lower() for kw in negative_keywords)
    
    # Check if reviews are overwhelmingly positive
    five_star_ratio = sum(1 for r in reviews if r.get("rating", 0) == 5) / max(len(reviews), 1)
    reviews_have_no_negatives = five_star_ratio > 0.85

    if summary_has_negatives and reviews_have_no_negatives:
        return 0.15, (
            "Platform's own AI summary mentions product issues, but scraped reviews show "
            "no negatives — strong sign of selective fake positive reviews"
        )
    return 0.0, None


def run_llm_analysis(reviews: list[dict], platform_summary: str) -> dict:
    """Signal 9: Deep LLM linguistic analysis."""
    sample = "\n".join([
        f"[Rating: {r.get('rating')}/5 | Verified: {r.get('verified', '?')}] "
        f"{r.get('text', '')[:200]}"
        for r in reviews[:20]
    ])

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )
    prompt = PromptTemplate(
        input_variables=["reviews", "platform_summary"],
        template=FAKE_REVIEW_PROMPT
    )
    chain = prompt | llm

    try:
        response = chain.invoke({
            "reviews": sample,
            "platform_summary": platform_summary or "Not available"
        })
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[Detective] LLM analysis failed: {e}")
        return {"llm_fake_score": 0.0, "red_flags": [], "platform_summary_contradiction": False, "verdict": "Unknown"}


# ─── Master Analyzer ────────────────────────────────────────────

def analyze_reviews(
    reviews: list[dict],
    original_rating: float,
    platform_summary: str = "Not available"
) -> dict:
    """
    Runs all 9 signals and combines them into a final trust score.

    reviews: list of dicts with keys:
        text (str), rating (int), date (str), verified (bool),
        location (str, optional), reviewer_name (str, optional)
    platform_summary: The AI-generated summary from Amazon/Flipkart's review section
    original_rating: The star rating shown on the product page
    """
    total = len(reviews)
    if total == 0:
        return {
            "fake_percentage": 0.0,
            "red_flags": ["No reviews available to analyze"],
            "adjusted_rating": original_rating,
            "trust_score": 0.5,
            "verdict": "Unknown"
        }

    red_flags = []
    heuristic_score = 0.0

    # Run signals 1–8 (heuristics — no LLM cost)
    signals = [
        check_unverified_ratio(reviews),
        check_star_distribution(reviews),
        check_short_reviews(reviews),
        check_date_clustering(reviews),
        check_location_clustering(reviews),
        check_duplicate_reviews(reviews),
        check_reviewer_name_patterns(reviews),
        check_platform_summary(reviews, platform_summary),
    ]

    for score_contribution, flag_message in signals:
        heuristic_score += score_contribution
        if flag_message:
            red_flags.append(flag_message)

    heuristic_score = min(heuristic_score, 1.0)

    # Run signal 9 — LLM deep analysis
    llm_result = run_llm_analysis(reviews, platform_summary)
    llm_fake_score = llm_result.get("llm_fake_score", 0.0)

    if llm_result.get("platform_summary_contradiction") and \
       "Platform's own AI summary" not in " ".join(red_flags):
        red_flags.append("LLM detected contradiction between individual reviews and platform summary")

    red_flags.extend(llm_result.get("red_flags", []))

    # ─── Combine all signals (weighted) ─────────────────────────
    # Heuristics: 60% weight (8 signals combined)
    # LLM analysis: 40% weight (deeper but single score)
    combined_fake_pct = (0.60 * heuristic_score) + (0.40 * llm_fake_score)
    combined_fake_pct = min(combined_fake_pct, 1.0)

    # Adjusted rating: penalise proportionally to fake confidence
    # Max penalty: 40% reduction (if 100% fake)
    adjusted_rating = original_rating * (1 - combined_fake_pct * 0.40)

    return {
        "fake_percentage": round(combined_fake_pct, 2),
        "red_flags": list(dict.fromkeys(red_flags)),  # deduplicate
        "adjusted_rating": round(adjusted_rating, 2),
        "trust_score": round(1 - combined_fake_pct, 2),
        "verdict": llm_result.get("verdict", "Unknown"),
        "heuristic_score": round(heuristic_score, 2),
        "llm_score": round(llm_fake_score, 2),
        "platform_summary_used": platform_summary != "Not available"
    }
```

### How to Get the Platform AI Summary

Both Amazon and Flipkart display an AI-generated summary of all reviews at the top of the reviews section. You scrape this once per product (much easier than scraping all reviews).

```python
# scrapers/review_summary_scraper.py

import asyncio
from playwright.async_api import async_playwright

async def get_amazon_review_summary(product_url: str) -> str:
    """
    Scrapes Amazon's AI-generated review summary from the product page.
    Located in the section: 'Customers say' or 'About this item'.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(product_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Amazon's AI summary selector (may vary — inspect page to confirm)
        selectors = [
            "[data-hook='cr-lighthouse-summary']",
            ".cr-lighthouse-summary",
            "[data-hook='review-collapsed'] span",
        ]
        for selector in selectors:
            el = await page.query_selector(selector)
            if el:
                text = await el.inner_text()
                await browser.close()
                return text.strip()

        await browser.close()
        return "Not available"


async def get_flipkart_review_summary(product_url: str) -> str:
    """
    Scrapes Flipkart's review highlights section.
    Located under 'Review Highlights' on the product page.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(product_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        selectors = [
            "._3OrRlq",        # Flipkart review highlights class
            "._2-N8zT",        # Alternative selector
            "[class*='review-summary']"
        ]
        for selector in selectors:
            el = await page.query_selector(selector)
            if el:
                text = await el.inner_text()
                await browser.close()
                return text.strip()

        await browser.close()
        return "Not available"
```

> ⚠️ **Note on Selectors:** Amazon and Flipkart change their CSS class names frequently. Always inspect the live page with browser DevTools (`F12`) before building. Use `data-hook` attributes on Amazon — they're more stable than class names.


---

## 10. Phase 5 — Scoring & Ranking Engine

**File:** `core/scoring.py`

### The Complete Formula

```python
# core/scoring.py

import math
import numpy as np

def compute_all_scores(product: dict, profile: dict) -> dict:
    """
    Computes all individual component scores for a product.
    Each score is normalized to [0, 1].
    """
    scores = {}
    
    budget = profile.get("budget_inr") or 100000
    price = product.get("price", 0)
    
    # ─── Score 1: Price Score ───────────────────────────────────
    # How good is the price vs the user's budget?
    # 1.0 = way under budget, 0.0 = over budget
    if price <= 0:
        scores["price_score"] = 0.0
    elif price > budget * 1.1:  # 10% over budget = 0
        scores["price_score"] = 0.0
    else:
        scores["price_score"] = max(0, (budget - price) / budget)
    
    # ─── Score 2: True Rating Score ────────────────────────────
    # Adjusted rating (post fake-review detection) / 5
    adjusted_rating = product.get("adjusted_rating", product.get("rating", 0))
    scores["rating_score"] = min(adjusted_rating / 5.0, 1.0)
    
    # ─── Score 3: Popularity Score ─────────────────────────────
    # Log scale to prevent 1M reviews dominating over 10K reviews
    reviews = product.get("reviews_count", 0)
    scores["popularity_score"] = math.log1p(reviews) / math.log1p(1000000)
    # normalize: log(1M+1) as max expected
    
    # ─── Score 4: Spec Match Score ─────────────────────────────
    # Computed by LLM (see run_spec_match below)
    scores["spec_score"] = product.get("spec_score", 0.5)
    
    # ─── Score 5: Price History Score ──────────────────────────
    # Is current price below 90-day average?
    scores["price_history_score"] = product.get("price_history_score", 0.5)
    
    # ─── Score 6: Seller Trust Score ───────────────────────────
    scores["seller_score"] = compute_seller_score(product)
    
    # ─── Score 7: Review Trust Score ───────────────────────────
    scores["trust_score"] = product.get("trust_score", 0.5)
    
    return scores


def compute_seller_score(product: dict) -> float:
    """
    Seller trust: based on platform and seller type.
    """
    platform = product.get("platform", "").lower()
    seller = product.get("seller", "").lower()
    
    score = 0.5  # baseline
    
    # Sold by official platform = high trust
    if "amazon" in seller and "amazon" in platform:
        score = 0.9
    elif "flipkart" in seller and "flipkart" in platform:
        score = 0.85

    # Third-party sellers: neutral
    return score


def run_spec_match(product: dict, profile: dict) -> float:
    """
    Uses LLM to compare product specs vs user requirements.
    Returns 0.0 to 1.0.
    """
    from langchain_groq import ChatGroq
    from langchain.prompts import PromptTemplate
    import os, json

    SPEC_PROMPT = """
    Compare the product specs against the user's requirements.
    Handle any product category — electronics, fashion, appliances, consumables, furniture, or other.

    User Requirements:
    Mandatory: {mandatory_specs}
    Preferred: {preferred_specs}
    Use Case: {use_case}

    Product: {product_title}
    Product Specs: {product_specs}

    Return ONLY a JSON:
    {{
      "match_score": <float 0.0 to 1.0>,
      "matched": ["list of matched requirements"],
      "missed": ["list of missed requirements"],
      "reasoning": "<one sentence>"
    }}
    """

    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
    prompt = PromptTemplate(
        input_variables=["mandatory_specs", "preferred_specs", "use_case", "product_title", "product_specs"],
        template=SPEC_PROMPT
    )
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "mandatory_specs": json.dumps(profile.get("mandatory_specs", {})),
            "preferred_specs": json.dumps(profile.get("preferred_specs", {})),
            "use_case": profile.get("use_case", ""),
            "product_title": product.get("title", ""),
            "product_specs": json.dumps(product.get("specs", {}))
        })
        result = json.loads(response.content.strip())
        return result.get("match_score", 0.5), result
    except:
        return 0.5, {}
```

---

## 11. Phase 6 — LangGraph Orchestration

**File:** `core/graph.py`

This is the **brain** — LangGraph connects all agents into a pipeline with state.

```python
# core/graph.py

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
import json

# ─── Shared State (passed between all nodes) ────────────────────

class AgentState(TypedDict):
    user_input: str
    profile: Optional[dict]           # Output of Agent 1
    raw_products: Optional[List[dict]] # Output of Agent 2
    products_with_history: Optional[List[dict]]  # Output of Agent 3
    products_with_trust: Optional[List[dict]]    # Output of Agent 4
    ranked_products: Optional[List[dict]]        # Output of Agent 5
    error: Optional[str]


# ─── Node Functions ─────────────────────────────────────────────

def node_profiler(state: AgentState) -> AgentState:
    print("🧠 [Agent 1] Parsing intent...")
    from agents.profiler import run_profiler
    try:
        profile = run_profiler(state["user_input"])
        return {**state, "profile": profile}
    except Exception as e:
        return {**state, "error": f"Profiler failed: {str(e)}"}


def node_scraper(state: AgentState) -> AgentState:
    print("🌐 [Agent 2] Collecting products...")
    from agents.scraper import run_scraper
    try:
        products = run_scraper(state["profile"])
        return {**state, "raw_products": products}
    except Exception as e:
        return {**state, "error": f"Scraper failed: {str(e)}"}


def node_historian(state: AgentState) -> AgentState:
    print("📈 [Agent 3] Computing relative price scores...")
    from agents.historian import run_historian
    enriched = run_historian(state["raw_products"])
    return {**state, "products_with_history": enriched}


def node_detective(state: AgentState) -> AgentState:
    print("🔍 [Agent 4] Analyzing reviews...")
    from agents.detective import analyze_reviews
    from scrapers.review_summary_scraper import get_amazon_review_summary, get_flipkart_review_summary
    import asyncio

    enriched = []
    for product in state["products_with_history"]:
        rating = product.get("rating", 4.0)
        platform = product.get("platform", "")
        url = product.get("url", "")

        # Fetch platform's own AI review summary
        try:
            if "Amazon" in platform and url:
                platform_summary = asyncio.run(get_amazon_review_summary(url))
            elif "Flipkart" in platform and url:
                platform_summary = asyncio.run(get_flipkart_review_summary(url))
            else:
                platform_summary = "Not available"
        except Exception:
            platform_summary = "Not available"

        # Mock individual reviews for demo — replace with real review scraping in production
        mock_reviews = [
            {"text": "Good product, fast delivery", "rating": 5, "verified": True,
             "date": "2024-08-01", "location": "Mumbai", "reviewer_name": "Rahul K."},
            {"text": "Amazing!", "rating": 5, "verified": False,
             "date": "2024-08-01", "location": "Mumbai", "reviewer_name": "Amazon Customer"},
            {"text": "Works as expected, battery is decent but heats a little under load",
             "rating": 4, "verified": True, "date": "2024-07-15",
             "location": "Delhi", "reviewer_name": "Priya M."},
            {"text": "Very nice product very good", "rating": 5, "verified": False,
             "date": "2024-08-01", "location": "Mumbai", "reviewer_name": "User1234"},
        ]

        trust_analysis = analyze_reviews(mock_reviews, rating, platform_summary)
        product["adjusted_rating"] = trust_analysis["adjusted_rating"]
        product["trust_score"] = trust_analysis["trust_score"]
        product["fake_percentage"] = trust_analysis["fake_percentage"]
        product["review_red_flags"] = trust_analysis["red_flags"]
        product["review_verdict"] = trust_analysis["verdict"]
        product["platform_summary"] = platform_summary
        enriched.append(product)

    return {**state, "products_with_trust": enriched}


def node_evaluator(state: AgentState) -> AgentState:
    print("🏆 [Agent 5] Scoring & ranking...")
    from core.scoring import compute_all_scores
    from core.weights import get_weights
    from agents.scoring import run_spec_match
    
    profile = state["profile"]
    weights = get_weights(profile["category"])
    
    scored = []
    for product in state["products_with_trust"]:
        # Get spec match score from LLM
        spec_score, spec_detail = run_spec_match(product, profile)
        product["spec_score"] = spec_score
        product["spec_detail"] = spec_detail
        
        # Compute all component scores
        scores = compute_all_scores(product, profile)
        
        # Final weighted score
        final_score = (
            weights["price"]        * scores["price_score"] +
            weights["rating"]       * scores["rating_score"] +
            weights["popularity"]   * scores["popularity_score"] +
            weights["spec"]         * scores["spec_score"] +
            weights["price_history"]* scores["price_history_score"] +
            weights["seller"]       * scores["seller_score"] +
            weights["trust"]        * scores["trust_score"]
        )
        
        product["scores"] = scores
        product["final_score"] = round(final_score * 100, 1)  # out of 100
        scored.append(product)
    
    # Sort descending by final score
    ranked = sorted(scored, key=lambda x: x["final_score"], reverse=True)[:10]
    
    # Add rank and generate "why" explanation
    for i, product in enumerate(ranked):
        product["rank"] = i + 1
        product["why"] = generate_why(product, profile)
    
    return {**state, "ranked_products": ranked}


def generate_why(product: dict, profile: dict) -> list[str]:
    reasons = []
    scores = product.get("scores", {})
    
    if scores.get("price_score", 0) > 0.7:
        savings = profile.get("budget_inr", 0) - product.get("price", 0)
        reasons.append(f"₹{savings:,.0f} under your budget")
    
    if scores.get("spec_score", 0) > 0.8:
        reasons.append("Matches over 80% of your required specs")
    
    history = product.get("price_history", {})
    if history.get("is_good_deal"):
        pct = history.get("vs_average_pct", 0)
        reasons.append(f"Currently {pct}% below 90-day average price")
    
    if scores.get("trust_score", 0) > 0.8:
        reasons.append("Highly trusted seller with authentic reviews")
    
    if product.get("fake_percentage", 0) > 0.2:
        reasons.append(f"⚠️ Warning: {int(product['fake_percentage']*100)}% potentially fake reviews detected")
    
    return reasons


# ─── Build the Graph ────────────────────────────────────────────

def build_pipeline():
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("profiler", node_profiler)
    graph.add_node("scraper", node_scraper)
    graph.add_node("historian", node_historian)
    graph.add_node("detective", node_detective)
    graph.add_node("evaluator", node_evaluator)
    
    # Add edges (linear pipeline)
    graph.set_entry_point("profiler")
    graph.add_edge("profiler", "scraper")
    graph.add_edge("scraper", "historian")
    graph.add_edge("historian", "detective")
    graph.add_edge("detective", "evaluator")
    graph.add_edge("evaluator", END)
    
    return graph.compile()


# ─── Run the pipeline ───────────────────────────────────────────

def run_pipeline(user_input: str) -> list[dict]:
    pipeline = build_pipeline()
    
    initial_state = AgentState(
        user_input=user_input,
        profile=None,
        raw_products=None,
        products_with_history=None,
        products_with_trust=None,
        ranked_products=None,
        error=None
    )
    
    result = pipeline.invoke(initial_state)
    
    if result.get("error"):
        raise Exception(result["error"])
    
    return result["ranked_products"]
```

---

## 12. Phase 7 — Streamlit UI

**File:** `ui/app.py`

```python
# ui/app.py

import streamlit as st
import sys
sys.path.append("..")

from core.graph import run_pipeline

# ─── Page Config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Agentic Commerce",
    page_icon="🛒",
    layout="wide"
)

# ─── Header ─────────────────────────────────────────────────────
st.title("🛒 Agentic Commerce")
st.markdown("**AI-powered product discovery across Amazon.in, Flipkart & Croma**")
st.divider()

# ─── Input ──────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])

with col1:
    user_input = st.text_input(
        "What are you looking for?",
        placeholder="e.g. I want a gaming laptop under ₹80,000 with RTX GPU and good battery",
        label_visibility="collapsed"
    )

with col2:
    search_btn = st.button("🔍 Search", use_container_width=True, type="primary")

# ─── Run Pipeline ───────────────────────────────────────────────
if search_btn and user_input:
    
    with st.spinner("🤖 Agents working... This may take 30–60 seconds"):
        
        progress = st.progress(0)
        status = st.empty()
        
        status.text("🧠 Agent 1: Understanding your requirements...")
        progress.progress(15)
        
        try:
            products = run_pipeline(user_input)
            progress.progress(100)
            status.empty()
            
        except Exception as e:
            st.error(f"Pipeline failed: {str(e)}")
            st.stop()
    
    st.success(f"✅ Found and ranked **{len(products)} products** for you!")
    st.divider()
    
    # ─── Results ────────────────────────────────────────────────
    for product in products:
        rank = product["rank"]
        score = product["final_score"]
        
        # Score color
        if score >= 80:
            score_color = "🟢"
        elif score >= 60:
            score_color = "🟡"
        else:
            score_color = "🔴"
        
        with st.container():
            col_img, col_info, col_score = st.columns([1, 4, 2])
            
            with col_img:
                if product.get("thumbnail"):
                    st.image(product["thumbnail"], width=120)
                else:
                    st.markdown("🖼️ No image")
            
            with col_info:
                st.markdown(f"### #{rank} — {product['title'][:80]}")
                
                # Price and platform badge
                price = product.get("price", 0)
                platform = product.get("platform", "")
                adj_rating = product.get("adjusted_rating", product.get("rating", 0))
                
                st.markdown(f"**₹{price:,.0f}** &nbsp; | &nbsp; ⭐ {adj_rating:.1f} (adjusted) &nbsp; | &nbsp; 🏪 {platform}")
                
                # Why this product?
                if product.get("why"):
                    for reason in product["why"]:
                        if "⚠️" in reason:
                            st.warning(reason)
                        else:
                            st.markdown(f"✅ {reason}")
                
                # Red flags
                if product.get("review_red_flags"):
                    with st.expander("⚠️ Review Analysis Details"):
                        for flag in product["review_red_flags"]:
                            st.markdown(f"- {flag}")
                
                # Link
                if product.get("url"):
                    st.link_button("View Product →", product["url"])
            
            with col_score:
                st.metric(
                    label="Agent Score",
                    value=f"{score_color} {score}/100"
                )
                
                # Score breakdown
                scores = product.get("scores", {})
                if scores:
                    with st.expander("Score Breakdown"):
                        for name, val in scores.items():
                            bar_val = int(val * 100)
                            label = name.replace("_", " ").title()
                            st.markdown(f"**{label}:** {bar_val}/100")
                            st.progress(val)
        
        st.divider()

# ─── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## How it works")
    st.markdown("""
    1. 🧠 **Profiler** — Understands your request
    2. 🌐 **Scraper** — Searches 2 platforms (~40–50 products)
    3. 📈 **Historian** — Checks price history
    4. 🔍 **Detective** — Runs 9 fake review signals
    5. 🏆 **Evaluator** — Ranks & explains
    """)

    st.divider()
    st.markdown("**Platforms searched:**")
    st.markdown("🛍️ Amazon.in")
    st.markdown("🛍️ Flipkart")

    st.divider()
    st.caption("Powered by LangGraph + OpenAI")
```

**Run it:**
```bash
cd agentic-commerce
streamlit run ui/app.py
```

---

## 13. The Ranking Formula (Full Math)

### Final Score Equation

```
S_total = (W_price × P_score) + (W_rating × R_score) + (W_pop × Pop_score)
        + (W_spec × Spec_score) + (W_hist × Hist_score)
        + (W_seller × Seller_score) + (W_trust × Trust_score)
```

### Individual Score Formulas

| Score | Formula | Notes |
|-------|---------|-------|
| **Price Score** | `(budget - price) / budget` | 0 if over budget |
| **Rating Score** | `adjusted_rating / 5.0` | Uses fake-adjusted rating |
| **Popularity Score** | `log(1 + reviews) / log(1,000,001)` | Log scale, prevents outliers |
| **Spec Score** | LLM returns 0–1 | Based on spec matching |
| **Price History Score** | `0.5 + (avg_90d - current) / avg_90d` | Clamped to [0,1] |
| **Seller Score** | Rule-based (0.5–0.9) | Based on platform & seller type |
| **Trust Score** | `1 - fake_percentage` | From review analysis |

### Adjusted Rating Formula

```
Adjusted Rating = Original Rating × (1 - fake_percentage × 0.5)

Example:
Original: 4.8 stars, 30% fake reviews
Adjusted: 4.8 × (1 - 0.3 × 0.5) = 4.8 × 0.85 = 4.08 stars
```

---

## 14. Dynamic Weights by Category

**File:** `core/weights.py`

```python
# core/weights.py

CATEGORY_WEIGHTS = {
    "electronics": {
        "spec":          0.30,   # Most important — does it have the right specs?
        "price":         0.20,   # Budget matters a lot
        "price_history": 0.15,   # Is it on sale or inflated?
        "rating":        0.15,   # Reviews matter
        "trust":         0.10,   # Fake review check
        "seller":        0.05,   # Seller trust
        "popularity":    0.05,   # Number of orders
    },
    "fashion": {
        "rating":        0.35,   # Subjective — reviews dominate
        "trust":         0.25,   # Fake reviews are rampant in fashion
        "price":         0.20,   # Price still matters
        "seller":        0.10,   # Trusted sellers
        "spec":          0.05,   # Size/color only
        "price_history": 0.03,
        "popularity":    0.02,
    },
    "appliances": {
        "spec":          0.25,
        "price":         0.20,
        "price_history": 0.20,   # Appliances go on big sales (festival season)
        "rating":        0.15,
        "seller":        0.10,
        "trust":         0.05,
        "popularity":    0.05,
    },
    "consumables": {
        "trust":         0.35,   # Safety critical — fake products are dangerous
        "rating":        0.30,
        "seller":        0.20,
        "price":         0.10,
        "spec":          0.03,
        "price_history": 0.01,
        "popularity":    0.01,
    },
    "furniture": {
        "rating":        0.30,
        "trust":         0.25,
        "price":         0.20,
        "seller":        0.15,
        "spec":          0.05,
        "price_history": 0.03,
        "popularity":    0.02,
    },
    "other": {
        # Default balanced weights
        "spec":          0.20,
        "price":         0.20,
        "rating":        0.20,
        "trust":         0.15,
        "seller":        0.10,
        "price_history": 0.10,
        "popularity":    0.05,
    }
}

def get_weights(category: str) -> dict:
    return CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["other"])
```

---

## 15. How to Run the Project

```bash
# Step 1: Start MongoDB (if using locally)
mongod --dbpath ./data/db

# Step 2: Install Playwright browsers (one time)
playwright install chromium

# Step 3: Activate venv
source venv/bin/activate   # or venv\Scripts\activate on Windows

# Step 4: Test individual agents
python agents/profiler.py    # Test intent parsing
python agents/scraper.py     # Test product scraping

# Step 5: Run full pipeline test
python -c "
from core.graph import run_pipeline
results = run_pipeline('gaming laptop under 80000 RTX GPU')
for p in results[:3]:
    print(p['rank'], p['title'], p['final_score'])
"

# Step 6: Launch Streamlit UI
streamlit run ui/app.py
```

---

## 16. API Keys & Costs

### 💸 Everything is Free

| Service | Purpose | Cost | How to Get |
|---------|---------|------|-----------|
| **Groq API** | LLM for all AI tasks | ✅ **Free** (generous limits) | [console.groq.com](https://console.groq.com) — sign up with Google |
| **Playwright** | Web scraping Amazon + Flipkart | ✅ **Free** | `pip install playwright` |
| **MongoDB Atlas** | Database | ✅ **Free** (512MB forever) | [mongodb.com/atlas](https://mongodb.com/atlas) |
| **Streamlit** | Frontend + free deployment | ✅ **Free** | [streamlit.io](https://streamlit.io) |
| **LangChain / LangGraph** | Agent framework | ✅ **Free** | Open source |

**Total monthly cost: ₹0**

### Groq Free Tier Limits
Groq gives you **14,400 requests/day** on the free tier with `llama-3.1-8b-instant`. Each full pipeline run uses roughly 3–5 LLM calls (profiler + spec matching per product sample + fake review analysis). You can run ~2,000–4,000 searches per day for free. More than enough for development, demos, and college submissions.

---

## 17. Common Pitfalls & Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| Amazon returns 0 products | Bot detection or selector changed | Add longer `wait_for_timeout(3000)`, update CSS selectors |
| Flipkart login popup blocks scraping | Popup appears before content loads | Add the popup-dismiss code (already in scraper above) |
| Groq returns invalid JSON | Model didn't follow format | Add `try/except` + strip markdown fences before `json.loads()` |
| Streamlit times out | Pipeline takes 60–90s | Add `st.spinner` with progress messages so UI doesn't freeze |
| Price parsed as 0 | Currency symbol or comma in string | Use `re.sub(r'[^\d.]', '', text)` |
| Spec score always 0.5 | Product title has no specs | Pass full product title to LLM — it can infer specs from title |
| Groq rate limit hit | Too many parallel LLM calls | Add `time.sleep(0.5)` between LLM calls in the evaluator loop |
| Playwright install error | Browser not downloaded | Run `playwright install chromium` once after pip install |

---

## 18. Roadmap & Advanced Features

### ✅ 3-Day Build (Free Stack)
- [x] Groq API for all LLM tasks (zero cost)
- [x] Playwright scraping — Amazon.in + Flipkart
- [x] Intent parser — handles all categories
- [x] 9-signal fake review detection
- [x] Dynamic weights per category
- [x] Relative price scoring (no Keepa needed)
- [x] Streamlit UI with score breakdown

### Phase 2 — After Demo
- [ ] Keepa free tier for real Amazon price history (1 req/min)
- [ ] Real per-product review scraping (with location + reviewer name)
- [ ] MongoDB caching — don't re-scrape same query twice
- [ ] Product comparison table side-by-side

### Phase 3 — If You Launch It
- [ ] Deploy Streamlit free on streamlit.io
- [ ] User accounts + saved searches
- [ ] Price drop alert system (email when price falls)

---

## 🔑 Key Files Summary

| File | Role |
|------|------|
| `agents/profiler.py` | Converts user text → structured JSON |
| `agents/scraper.py` | Fetches 40–50 products from Amazon.in + Flipkart in parallel |
| `agents/historian.py` | Gets 90-day price history |
| `agents/detective.py` | 9-signal fake review detection + trust score |
| `scrapers/review_summary_scraper.py` | Scrapes Amazon/Flipkart AI review summaries |
| `core/scoring.py` | All scoring formulas |
| `core/weights.py` | Category-specific weights |
| `core/graph.py` | LangGraph pipeline connecting all agents |
| `ui/app.py` | Streamlit frontend |
| `.env` | API keys |

---

*Built with LangGraph · Groq API (Free) · Playwright · Streamlit · MongoDB Atlas*  
*Platforms: Amazon.in · Flipkart — 40–50 products compared per search · Total Cost: ₹0*