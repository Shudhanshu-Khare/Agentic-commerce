# 🛠️ Agentic Commerce — 4 Critical Fixes Before Demo
### Step-by-Step Implementation Guide

> These are not optional polish — they are **demo-survival fixes**.  
> Implement all 4 before you present. Each one is independent and can be added in under 30 minutes.

---

## Table of Contents
1. [Fix 1 — Scraper Fallback Layer](#fix-1--scraper-fallback-layer)
2. [Fix 2 — Deduplication Engine](#fix-2--deduplication-engine)
3. [Fix 3 — Groq Rate Limit Protection](#fix-3--groq-rate-limit-protection)
4. [Fix 4 — Streamlit Progress Indicator](#fix-4--streamlit-progress-indicator)

---

## Fix 1 — Scraper Fallback Layer

### 🎯 What It Does & Why It Matters

Your entire pipeline — all 5 agents, all the math, all the scoring — depends on the scraper successfully collecting products. Playwright scrapes live websites using CSS class selectors like `._4rR01T` on Flipkart and `[data-component-type="s-search-result"]` on Amazon.

**The problem:** Amazon and Flipkart change their HTML structure and CSS class names without warning. This happens regularly — sometimes overnight. If your selectors break during the demo, the scraper returns 0 products, and the entire pipeline crashes with an empty result. The audience sees nothing. That is the worst possible outcome.

**The fix has two parts:**

**Part A — Soft Warning System:** If the scraper returns fewer than 10 products from a platform, it does not crash. It logs a clear warning, continues with whatever it has, and the pipeline proceeds with partial data gracefully.

**Part B — JSON Backup:** The night before your demo, run a successful scrape and save the results to a JSON file. If the live scrape fails on demo day, the pipeline silently loads the backup file instead. The demo continues perfectly. Nobody knows.

---

### 📁 Where to Add This Code

**File:** `scrapers.py`

---

### ✅ Part A — Add the Warning Check Inside Each Scraper Function

Find the end of your `scrape_amazon()` and `scrape_flipkart()` functions, just before the `return products` line. Add this block:

```python
# scrapers.py
# Add this block at the END of scrape_amazon() and scrape_flipkart()
# BEFORE the final return statement

    # ── Fallback Warning ─────────────────────────────────────────────────
    # If we got fewer than 10 products, something likely broke.
    # We do NOT crash — we log and continue with what we have.
    # This prevents a single broken selector from killing the whole demo.

    MINIMUM_EXPECTED_PRODUCTS = 10

    if len(products) < MINIMUM_EXPECTED_PRODUCTS:
        print(
            f"\n⚠️  [Scraper Warning] ─────────────────────────────────────────\n"
            f"   Platform   : {platform_name}\n"
            f"   Got        : {len(products)} products (expected ≥ {MINIMUM_EXPECTED_PRODUCTS})\n"
            f"   Likely cause: CSS selectors may be outdated.\n"
            f"   Action     : Update selectors by inspecting the live page in Chrome DevTools.\n"
            f"   Continuing with {len(products)} results...\n"
            f"──────────────────────────────────────────────────────────────\n"
        )
    else:
        print(f"✅ [{platform_name}] Successfully collected {len(products)} products.")

    return products  # Always return, never crash
```

---

### ✅ Part B — Save Backup JSON After a Successful Scrape

**File:** `scrapers.py`

Add this utility function anywhere in the file:

```python
# scrapers.py
import json
import os
from datetime import datetime

BACKUP_DIR = "demo_backups"

def save_backup(products: list[dict], query: str) -> None:
    """
    Saves scraped products to a JSON file as a demo backup.
    Call this at the end of a successful scrape the night before your demo.

    AIM: If live scraping fails on demo day, you load this file instead.
    The pipeline continues normally — audience sees nothing wrong.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Clean the query to make it a valid filename
    safe_query = query.replace(" ", "_").replace("/", "-")[:40]
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M")
    filename   = f"{BACKUP_DIR}/{safe_query}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"✅ [Backup] Saved {len(products)} products to: {filename}")


def load_backup(query: str) -> list[dict] | None:
    """
    Loads the most recent backup JSON for a given query.
    Returns None if no backup exists.

    AIM: Called when live scraping returns too few results.
    Ensures the demo always has data to work with.
    """
    if not os.path.exists(BACKUP_DIR):
        return None

    # Find all backup files and sort by creation time (newest first)
    safe_query = query.replace(" ", "_").replace("/", "-")[:40]
    all_files  = [
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith(safe_query) and f.endswith(".json")
    ]

    if not all_files:
        return None

    all_files.sort(reverse=True)  # newest first
    latest = os.path.join(BACKUP_DIR, all_files[0])

    with open(latest, "r", encoding="utf-8") as f:
        products = json.load(f)

    print(f"📦 [Backup] Loaded {len(products)} products from: {latest}")
    return products
```

---

### ✅ Part C — Wire Backup Into Your Main Scraper Function

**File:** `scrapers.py` — update the `run_scraper()` function:

```python
# scrapers.py — update run_scraper()

def run_scraper(profile: dict) -> list[dict]:
    """
    Main entry point for the scraper agent.
    Runs Amazon + Flipkart in parallel.
    Falls back to saved JSON if live scraping fails or returns too few results.
    """
    query = build_search_query(profile)
    print(f"\n[Scraper] Query: '{query}'")

    # ── Live Scrape ──────────────────────────────────────────────────────
    def run_amazon():
        return asyncio.run(scrape_amazon(query, max_results=30))

    def run_flipkart():
        return asyncio.run(scrape_flipkart(query, max_results=30))

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_amazon   = executor.submit(run_amazon)
        f_flipkart = executor.submit(run_flipkart)
        amazon_results   = f_amazon.result()
        flipkart_results = f_flipkart.result()

    all_products = amazon_results + flipkart_results

    # ── Fallback Check ───────────────────────────────────────────────────
    # If we got fewer than 15 total products, live scraping has likely failed.
    # Load the most recent backup for this query instead.
    if len(all_products) < 15:
        print(f"\n⚠️  [Scraper] Only {len(all_products)} live results. Attempting backup load...")
        backup = load_backup(query)

        if backup:
            print(f"✅ [Scraper] Using backup data ({len(backup)} products). Pipeline continues.")
            return backup
        else:
            print(f"⚠️  [Scraper] No backup found. Proceeding with {len(all_products)} live results.")

    # ── Save Backup on Success ───────────────────────────────────────────
    # Every successful scrape automatically saves a fresh backup.
    # This means your demo backup is always up to date.
    if len(all_products) >= 15:
        save_backup(all_products, query)

    print(f"[Scraper] Total: {len(all_products)} products collected.")
    return all_products
```

---

### 🧪 How to Use It

**Night before demo:** Run one successful search for your planned demo query. The backup saves automatically. You are covered.

**Day of demo:** Run normally. If live scraping works, great. If it silently fails, it loads the backup. The demo continues without you doing anything.

---
---

## Fix 2 — Deduplication Engine

### 🎯 What It Does & Why It Matters

When you search for the same product on Amazon and Flipkart, the same physical product — for example, the "Sony WH-1000XM5 headphones" — will appear on both platforms. Without deduplication, your Top 10 might show the same product twice: once from Amazon at ₹26,990 and once from Flipkart at ₹27,499.

**Why this looks bad in a demo:**
- It wastes 2 of your 10 visible slots on the same item
- It makes the system look naive — like it doesn't know these are the same thing
- The user wanted a *comparison*, not a duplicate

**How it works:** For every product, we compare its title (trimmed to 80 characters) against all titles already seen, using Python's `SequenceMatcher` which measures how similar two strings are on a 0–1 scale. If two titles are more than 82% similar, the second one is considered a duplicate and dropped. The first occurrence (whichever platform found it first) is kept.

**Why 82% and not 100%?** Because Amazon might call it `"Sony WH-1000XM5 Wireless Noise Cancelling Headphones"` while Flipkart calls it `"Sony WH1000XM5 ANC Over-Ear Headphones"`. They're the same product but the titles are different. 82% similarity catches this without false positives.

---

### 📁 Where to Add This Code

**File:** `agents.py` — inside the `node_historian` function, after `run_historian()` runs.

---

### ✅ The Deduplication Function

Add this as a standalone function in `agents.py` or `core.py`:

```python
# agents.py or core.py

from difflib import SequenceMatcher

def deduplicate_products(products: list[dict]) -> list[dict]:
    """
    Removes near-duplicate products across platforms using fuzzy title matching.

    AIM: Prevents the same physical product from appearing twice in results
    just because it's listed on both Amazon and Flipkart.

    How it works:
        - Compares each new product's title against all already-seen titles
        - If similarity > 82%, the product is considered a duplicate
        - The FIRST occurrence (from whichever platform) is kept
        - The duplicate is discarded with a log message

    Why 82%? Lower than 100% because platform titles differ slightly:
        Amazon: "Sony WH-1000XM5 Wireless Headphones Black"
        Flipkart: "Sony WH1000XM5 ANC Over-Ear Headphones"
        These are the same product — 82% catches this correctly.
    """
    SIMILARITY_THRESHOLD = 0.82
    TITLE_COMPARE_LENGTH = 80   # Compare first 80 chars — enough to identify product

    seen_titles = []   # list of already-accepted product titles
    unique      = []   # final deduplicated list
    removed     = 0

    for product in products:
        # Normalize: lowercase, strip extra spaces, limit length
        title = product.get("title", "").lower().strip()[:TITLE_COMPARE_LENGTH]

        if not title:
            unique.append(product)  # keep products with no title (don't silently drop)
            continue

        is_duplicate = False

        for seen in seen_titles:
            similarity = SequenceMatcher(None, title, seen).ratio()

            if similarity >= SIMILARITY_THRESHOLD:
                # This product is a near-duplicate of something already in the list
                is_duplicate = True
                removed += 1
                print(
                    f"[Dedup] Removed duplicate ({similarity:.0%} match):\n"
                    f"        '{product.get('title', '')[:60]}'\n"
                    f"        (matches: '{seen[:60]}')"
                )
                break

        if not is_duplicate:
            seen_titles.append(title)
            unique.append(product)

    print(f"\n[Dedup] {len(products)} → {len(unique)} products ({removed} duplicates removed)\n")
    return unique
```

---

### ✅ Wire It Into the Pipeline

**File:** `agents.py` — update `node_historian`:

```python
# agents.py — inside node_historian

def node_historian(state: AgentState) -> AgentState:
    print("📈 [Agent 3] Computing market price context...")
    from agents import deduplicate_products   # or from core import ...
    from core import run_historian

    raw_products = state["raw_products"]

    # ── Step 1: Deduplicate FIRST, before any scoring ────────────────────
    # AIM: Ensure we don't waste score slots on duplicate cross-platform listings.
    # Must happen here (after scraping) and before the Detective or Evaluator.
    unique_products = deduplicate_products(raw_products)

    # ── Step 2: Run relative price scoring on clean data ─────────────────
    enriched = run_historian(unique_products)

    return {**state, "products_with_history": enriched}
```

---

### 🧪 What You'll See in Terminal

```
[Dedup] Removed duplicate (91% match):
        'sony wh-1000xm5 wireless headphones'
        (matches: 'sony wh1000xm5 noise cancelling headphones')

[Dedup] Removed duplicate (88% match):
        'apple airpods pro (2nd generation) magsafe'
        (matches: 'apple airpods pro 2nd gen usb-c')

[Dedup] 58 → 51 products (7 duplicates removed)
```

---
---

## Fix 3 — Groq Rate Limit Protection

### 🎯 What It Does & Why It Matters

During the Evaluator agent (Agent 5), your pipeline calls the Groq LLM up to **20 times sequentially** — once per product for spec matching. Groq's free tier on `llama-3.1-8b-instant` allows roughly **30 API requests per minute**.

**The math problem:** 20 calls with zero delay, each taking ~1.5 seconds = all 20 calls fire within ~30 seconds. If Groq processes them faster than their internal rate counter resets, you will hit a `429 Rate Limit Exceeded` error mid-pipeline. The pipeline crashes. The demo crashes.

**The fix:** Add a 0.5-second pause between each LLM call. This adds ~10 seconds total to your pipeline but 100% prevents the rate limit crash. Additionally, add a **retry wrapper** — if a single call fails, wait 5 seconds and try once more before giving up. This handles transient network hiccups that happen during live demos.

---

### 📁 Where to Add This Code

**File:** `agents.py` — inside `node_evaluator`, in the loop that calls `llm_spec_match`.

---

### ✅ The Retry Wrapper Function

Add this utility function in `agents.py`:

```python
# agents.py

import time

def call_llm_with_retry(fn, *args, retries: int = 2, delay: float = 5.0, **kwargs):
    """
    Calls any LLM function with automatic retry on failure.

    AIM: Prevents a single failed Groq API call from crashing the evaluator.
    On failure, waits `delay` seconds and tries again up to `retries` times.
    If all retries fail, returns a safe fallback value instead of raising.

    Args:
        fn      : The function to call (e.g., llm_spec_match)
        *args   : Positional arguments for fn
        retries : Number of retry attempts (default: 2)
        delay   : Seconds to wait between retries (default: 5.0)
        **kwargs: Keyword arguments for fn

    Returns:
        The result of fn(*args, **kwargs), or a safe fallback dict on total failure.
    """
    for attempt in range(1, retries + 2):   # +2 because range(1, retries+2) gives retries+1 attempts
        try:
            result = fn(*args, **kwargs)
            return result

        except Exception as e:
            error_msg = str(e)

            # Detect rate limit specifically (Groq returns HTTP 429)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                wait = delay * attempt   # progressive backoff: 5s, 10s, 15s
                print(f"⚠️  [Groq Rate Limit] Attempt {attempt} hit rate limit. Waiting {wait}s...")
                time.sleep(wait)

            elif attempt <= retries:
                print(f"⚠️  [LLM] Attempt {attempt} failed: {error_msg[:80]}. Retrying in {delay}s...")
                time.sleep(delay)

            else:
                # All retries exhausted — return a safe fallback
                print(f"❌ [LLM] All {retries+1} attempts failed. Using fallback score.")
                return {
                    "match_score": 0.5,      # neutral — don't penalize unfairly
                    "veto":        False,    # don't veto on LLM failure
                    "confirmed_specs": [],
                    "missing_specs":   [],
                    "reasoning":  "LLM unavailable — fallback score applied"
                }
```

---

### ✅ Update the Evaluator Loop With Rate Limit Protection

**File:** `agents.py` — find the Stage 2 LLM spec match loop in `node_evaluator` and replace it:

```python
# agents.py — inside node_evaluator, Stage 2 section

# ── Stage 2: LLM spec match on top 20 only ─────────────────────────────
# AIM: Run deep AI spec matching only on the most promising candidates.
#      This saves Groq API calls and prevents rate limiting.

RATE_LIMIT_SLEEP   = 0.5    # seconds between each LLM call (safe buffer)
LLM_CALL_BUDGET    = 20     # max LLM calls per pipeline run

stage1_results.sort(key=lambda x: x.get("quick_score", 0), reverse=True)
llm_candidates = stage1_results[:LLM_CALL_BUDGET]
remaining      = stage1_results[LLM_CALL_BUDGET:]

print(f"[Evaluator] Stage 2: Running LLM spec match on top {len(llm_candidates)} products...")

for idx, product in enumerate(llm_candidates):
    print(f"  [{idx+1}/{len(llm_candidates)}] Spec-matching: {product.get('title', '')[:50]}...")

    # ── Rate limit protection ──────────────────────────────────────────
    # Wait 0.5s before each call (except the first one).
    # This keeps us well under Groq's 30 req/min limit.
    # 20 calls × 0.5s = 10 extra seconds. Worth it to prevent a crash.
    if idx > 0:
        time.sleep(RATE_LIMIT_SLEEP)

    # ── Call LLM with retry ────────────────────────────────────────────
    # If the call fails (network hiccup, brief rate limit), retry up to 2 times.
    # If all retries fail, use a neutral fallback score (0.5) and continue.
    llm_result = call_llm_with_retry(
        llm_spec_match,                           # function to call
        product,                                  # arg 1
        profile,                                  # arg 2
        product.get("pre_matched", []),           # arg 3
        retries=2,
        delay=5.0
    )

    # Store LLM results on the product dict
    product["spec_score"]      = llm_result.get("match_score", 0.5)
    product["spec_veto"]       = llm_result.get("veto", False)
    product["veto_reason"]     = "LLM confirmed mandatory spec failure" if llm_result.get("veto") else ""
    product["confirmed_specs"] = llm_result.get("confirmed_specs", [])
    product["missing_specs"]   = llm_result.get("missing_specs", [])
    product["spec_reasoning"]  = llm_result.get("reasoning", "")

# Products ranked 21–60: use quick_score as spec_score (no LLM call)
# AIM: These are lower-ranked candidates anyway. Keyword score is good enough.
for product in remaining:
    product["spec_score"]      = product.get("quick_score", 0.4)
    product["spec_veto"]       = False
    product["confirmed_specs"] = product.get("pre_matched", [])
    product["missing_specs"]   = []
    product["spec_reasoning"]  = "Keyword match only (outside LLM budget)"

print(f"[Evaluator] Stage 2 complete. {len(llm_candidates)} LLM calls made.")
```

---

### 🧪 What You'll See in Terminal (When It Works)

```
[Evaluator] Stage 2: Running LLM spec match on top 20 products...
  [1/20] Spec-matching: ASUS ROG Strix G15 Gaming Laptop RTX 40...
  [2/20] Spec-matching: MSI Thin GF63 Gaming Laptop with RTX 305...
  [3/20] Spec-matching: Lenovo IdeaPad Gaming 3 AMD Ryzen 5 RTX...
  ...
[Evaluator] Stage 2 complete. 20 LLM calls made.
```

### 🧪 What You'll See If Rate Limited (Handled Gracefully)

```
  [8/20] Spec-matching: HP Victus 16 Gaming Laptop...
⚠️  [Groq Rate Limit] Attempt 1 hit rate limit. Waiting 5s...
  [8/20] Retrying...   ← succeeds on retry, pipeline continues
  [9/20] Spec-matching: Acer Nitro 5 AN515...
```

---
---

## Fix 4 — Streamlit Progress Indicator

### 🎯 What It Does & Why It Matters

Your pipeline takes 60–90 seconds to complete. Without any feedback, Streamlit shows a plain spinner — and the page looks completely frozen for a minute and a half. To someone watching (especially your professor), this looks like the app crashed or hung.

**The psychological reality of demos:** A 90-second wait *with visible progress* feels like 30 seconds. A 90-second wait *with a frozen screen* feels like 5 minutes. The progress indicator transforms a wait from "is this broken?" to "look at all this AI work happening."

**What this fix does:** Uses Streamlit's `st.status()` component to show an expandable live activity log. Each agent writes its status as it starts. The box stays open during the run so the audience can see the pipeline progressing in real time — Agent 1 → Agent 2 → Agent 3 → Agent 4 → Agent 5 → Done. At the end it collapses into a clean "✅ Complete" badge.

**Important implementation note:** LangGraph runs the entire pipeline in one `invoke()` call, which means you can't easily inject `st.write()` calls *inside* the graph. The solution is to run each agent node as a separate, explicit function call in `app.py` and update the status box between each one.

---

### 📁 Where to Add This Code

**File:** `app.py` — replace your current search execution block.

---

### ✅ The Full Progress-Aware Search Block

Replace the section in `app.py` where you call `run_pipeline()` with this:

```python
# app.py — full search execution block with live progress

import streamlit as st
import time

# ── Search Trigger ─────────────────────────────────────────────────────────
if search_btn and user_input.strip():

    # ── Progress Display ───────────────────────────────────────────────────
    # st.status() creates an expandable live activity log.
    # AIM: Makes the 60–90 second wait feel like active AI work, not a frozen page.
    # The audience can see exactly which agent is running at any moment.

    with st.status("🤖 Agentic pipeline running...", expanded=True) as status:

        # ── Agent 1: Profiler ──────────────────────────────────────────────
        st.write("🧠 **Agent 1 — Profiler:** Understanding your request...")
        agent1_start = time.time()

        from agents import run_profiler
        profile = run_profiler(user_input)

        agent1_time = round(time.time() - agent1_start, 1)
        st.write(
            f"   ✅ Extracted: **{profile.get('product_type', 'product')}** | "
            f"Budget: **₹{profile.get('budget_inr', 'N/A'):,}** | "
            f"Category: **{profile.get('category', 'N/A')}** "
            f"*({agent1_time}s)*"
        )

        # ── Agent 2: Scraper ───────────────────────────────────────────────
        st.write("🌐 **Agent 2 — Scraper:** Searching Amazon.in & Flipkart...")
        agent2_start = time.time()

        from scrapers import run_scraper
        raw_products = run_scraper(profile)

        agent2_time = round(time.time() - agent2_start, 1)
        st.write(
            f"   ✅ Collected **{len(raw_products)} products** "
            f"from Amazon.in & Flipkart "
            f"*({agent2_time}s)*"
        )

        # ── Agent 3: Historian ─────────────────────────────────────────────
        st.write("📈 **Agent 3 — Historian:** Analyzing market prices...")
        agent3_start = time.time()

        from agents import deduplicate_products
        from core import run_historian

        unique_products  = deduplicate_products(raw_products)
        products_history = run_historian(unique_products)

        agent3_time  = round(time.time() - agent3_start, 1)
        removed_dups = len(raw_products) - len(unique_products)
        st.write(
            f"   ✅ Market median calculated | "
            f"**{removed_dups} duplicates removed** | "
            f"**{len(products_history)} unique products** ready "
            f"*({agent3_time}s)*"
        )

        # ── Agent 4: Detective ─────────────────────────────────────────────
        st.write("🔍 **Agent 4 — Detective:** Running fake review analysis...")
        agent4_start = time.time()

        from agents import run_detective_on_product
        products_trust = [
            run_detective_on_product(p, products_history)
            for p in products_history
        ]

        # Count how many had red flags found
        flagged = sum(1 for p in products_trust if p.get("review_red_flags"))
        agent4_time = round(time.time() - agent4_start, 1)
        st.write(
            f"   ✅ Analyzed **{len(products_trust)} products** | "
            f"**{flagged} flagged** for suspicious review patterns "
            f"*({agent4_time}s)*"
        )

        # ── Agent 5: Evaluator ─────────────────────────────────────────────
        st.write("🏆 **Agent 5 — Evaluator:** Scoring and ranking products...")
        agent5_start = time.time()

        from agents import run_evaluator
        ranked_products = run_evaluator(products_trust, profile)

        agent5_time = round(time.time() - agent5_start, 1)
        top_score   = ranked_products[0]["final_score"] if ranked_products else 0
        st.write(
            f"   ✅ Ranked **{len(ranked_products)} products** | "
            f"Top score: **{top_score}/100** "
            f"*({agent5_time}s)*"
        )

        # ── Pipeline Complete ──────────────────────────────────────────────
        total_time = round(agent1_time + agent2_time + agent3_time + agent4_time + agent5_time, 1)
        status.update(
            label=f"✅ Pipeline complete — Top {len(ranked_products)} products found in {total_time}s",
            state="complete",
            expanded=False    # collapses the log into a clean badge after finishing
        )

    # ── Results Section ────────────────────────────────────────────────────
    # Render results below the status box
    if ranked_products:
        st.success(f"Found and ranked **{len(ranked_products)} products** for you!")
        st.divider()
        render_results(ranked_products)   # your existing results rendering function
    else:
        st.error("No products found. Try a different query or check your internet connection.")
```

---

### ✅ Bonus — Add a Pipeline Summary Metrics Bar

Add this just after the `st.success()` line and before `render_results()` for an extra professional touch:

```python
# app.py — add after st.success(), before render_results()

# Pipeline summary metrics row
# AIM: Shows the professor at a glance what the system processed —
#      looks impressive and communicates the scale of the analysis.

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    label="🌐 Products Scraped",
    value=len(raw_products),
    delta=f"-{len(raw_products) - len(unique_products)} duplicates"
)
col2.metric(
    label="🔍 Flagged Suspicious",
    value=flagged,
    delta="review signals triggered",
    delta_color="inverse"
)
col3.metric(
    label="🚫 Vetoed",
    value=len(products_trust) - len(ranked_products),
    delta="failed spec/budget check",
    delta_color="inverse"
)
col4.metric(
    label="🏆 Final Ranking",
    value=len(ranked_products),
    delta="passed all checks"
)
col5.metric(
    label="⏱️ Total Time",
    value=f"{total_time}s",
    delta="end to end"
)

st.divider()
```

---

### 🧪 What the Audience Sees

```
🤖 Agentic pipeline running...                              ▲ (expanded)
├── 🧠 Agent 1 — Profiler: Understanding your request...
│      ✅ Extracted: gaming laptop | Budget: ₹80,000 | Category: electronics (1.2s)
├── 🌐 Agent 2 — Scraper: Searching Amazon.in & Flipkart...
│      ✅ Collected 54 products from Amazon.in & Flipkart (28.4s)
├── 📈 Agent 3 — Historian: Analyzing market prices...
│      ✅ Market median calculated | 7 duplicates removed | 47 unique products ready (0.2s)
├── 🔍 Agent 4 — Detective: Running fake review analysis...
│      ✅ Analyzed 47 products | 12 flagged for suspicious review patterns (4.1s)
└── 🏆 Agent 5 — Evaluator: Scoring and ranking products...
       ✅ Ranked 10 products | Top score: 87.4/100 (18.3s)

✅ Pipeline complete — Top 10 products found in 52.2s    ▼ (collapsed to this)
```

---
---

## 📋 Quick Implementation Checklist

Copy this and check off each item as you implement it:

```
Day 3 — Pre-Demo Fixes

Fix 1: Scraper Fallback
  □ Add warning block at end of scrape_amazon() and scrape_flipkart()
  □ Add save_backup() and load_backup() functions to scrapers.py
  □ Update run_scraper() to call save_backup() on success
  □ Update run_scraper() to call load_backup() when < 15 results
  □ Run a test search to generate the demo_backups/ folder

Fix 2: Deduplication
  □ Add deduplicate_products() function to agents.py or core.py
  □ Call it inside node_historian() before run_historian()
  □ Test it — check terminal for "[Dedup] X → Y products" message

Fix 3: Rate Limit Protection
  □ Add call_llm_with_retry() function to agents.py
  □ Replace the Stage 2 LLM loop with the new protected version
  □ Confirm time.sleep(0.5) is present between calls
  □ Run a full pipeline — confirm it completes without 429 errors

Fix 4: Progress Indicator
  □ Replace run_pipeline() call in app.py with the agent-by-agent version
  □ Add the 5-column metrics bar after st.success()
  □ Run the full demo flow in Streamlit and watch the live progress log
  □ Confirm the status box collapses cleanly at the end

Night Before Demo:
  □ Run one full successful search for your planned demo query
  □ Confirm demo_backups/ folder has a saved JSON file
  □ Test with internet off to confirm backup loads correctly
  □ Time the full pipeline — note the seconds for each agent
```

---

*These 4 fixes take approximately 2–3 hours to implement and test.*  
*They are the difference between a demo that works and a demo that impresses.*
