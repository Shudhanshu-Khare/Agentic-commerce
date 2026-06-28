# Agentic Commerce: End-to-End System Architecture

This document provides a comprehensive, step-by-step walkthrough of how Agentic Commerce processes a user query from raw text to a ranked, verified list of products.

---

## 🏗️ Phase 0: The Orchestrator (LangGraph)
The entire project is governed by a **StateGraph**. This ensures that data flows logically from one agent to the next. If any step fails, the graph handles the error or provides a safe fallback. Each agent receives the "state," modifies it, and passes it forward.

---

## 🧠 Step 1: Agent Profiler (Intent Extraction)
**Goal**: Turn a messy human sentence into a clean technical profile.
1.  **Input**: "I need a gaming laptop under 80000 with 16GB RAM for video editing."
2.  **Processing**: The profiler uses **LLama 3.1 (Groq)** to extract:
    *   **Category**: `electronics`
    *   **Product Type**: `gaming laptop`
    *   **Budget**: `80,000`
    *   **Mandatory Specs**: `{"ram": "16GB", "gpu": "gaming"}`
    *   **Use Case**: `video editing`
3.  **Output**: A structured `profile` JSON that all other agents use as their "instruction manual."

---

## 🌐 Step 2: Agent Scraper (Collection & Cleaning)
**Goal**: Gather raw data from the real world.
1.  **Execution**: It launches two sequential browser sessions using **Playwright**:
    *   **Amazon.in**: Searches for the product type and budget.
    *   **Flipkart**: Performs the same search.
2.  **Limits**: It collects a maximum of **30 products per platform** (60 total).
3.  **Deduplication**: It compares titles using Fuzzy Matching. If two items are 85% similar, one is discarded to avoid showing the same product twice.
4.  **Cleaning**: It removes "junk" results (e.g., sponsored ads that aren't products, or accessories like laptop bags when you asked for a laptop).

---

## 📈 Step 3: Agent Historian (Market Context)
**Goal**: Determine if a price is actually a "good deal" relative to the current day.
1.  **Market Benchmark**: It calculates the **Median Price** of all 60 collected products.
2.  **Price Positioning**: Every product is assigned a "Position" (e.g., Budget-friendly if it's in the bottom 20% of the price range).
3.  **Scoring**: If a product is cheaper than the market median, it gets a high **Price History Score**. This catches "marked-up" prices that are higher than they should be.

---

## 🔍 Step 4: Agent Detective (Trust & Authenticity)
**Goal**: Filter out products with fake reviews or manipulated reputations.
This uses a **Metadata-First** approach (no slow review scraping):
1.  **Signal 1 (Confidence)**: It penalizes "Suspect Perfection" (e.g., a 5.0⭐ rating with only 3 reviews is untrustworthy).
2.  **Signal 2 (Anomalies)**: It checks if a premium item (₹50k+) has a perfect score, which is rare for real products.
3.  **Signal 3 (Cross-Platform)**: If an item is 4.8⭐ on Amazon but 3.8⭐ on Flipkart, it triggers a major discrepancy warning.
4.  **Signal 4 (Review Velocity)**: It flags ultra-cheap items with huge review counts (listing manipulation).
5.  **LLM Gut-Check**: A final AI review of the numbers to see if the "story" the data tells is plausible.
6.  **Result**: An **Adjusted Rating** (e.g., a 4.5⭐ product might be demoted to 3.8⭐ if it is suspicious).

---

## 🏆 Step 5: Agent Evaluator (The Two-Stage Funnel)
**Goal**: Find the absolute best matches out of the 60 candidates.

### Stage A: Fast Pre-filter
*   It runs a **Keyword/Regex check**. If you asked for an "RTX" laptop and the title says "integrated graphics," it is **Vetoed** instantly without using any AI.

### Stage B: Selective AI Match
*   The AI (LLM) only looks at the **Top 20 survivors**. It deep-checks the specs to see if the product *truly* matches your use case.

### Stage C: Batch-Normalized Scoring
The final score (0–100) is calculated using 7 weighted components:
1.  **Spec Match (25%)**: How well it fits your hardware needs.
2.  **Price (15%)**: How well it fits your budget.
3.  **Rating (15%)**: Star rating, adjusted for trust and volume (Bayesian).
4.  **Popularity (15%)**: How many verified buyers have bought it.
5.  **Trust (10%)**: The Detective's authenticity score.
6.  **Seller (10%)**: Is it "Platform Verified" or a 3rd party?
7.  **Price History (10%)**: Is it cheaper than the market average today?

---

## 🏁 Final Step: Results & "Why" Generation
1.  **Ranking**: The products are sorted by their final score.
2.  **Veto Check**: Any product that failed a mandatory spec or is >15% over-budget is removed.
3.  **Logic-Based "Why"**: The system looks at the high scores and generates reasons automatically:
    *   "₹5,000 under budget"
    *   "Matches your RAM requirement"
    *   "Highly popular (10,000+ reviews)"
4.  **UI Display**: The Top 10 are rendered in the Streamlit frontend with a detailed breakdown of their scores.

---

### 🛡️ Key Protection Logic
*   **Bayesian Rating**: `(confidence * rating) + ((1 - confidence) * 3.5)`. This mathematically forces products with very low reviews toward an "Average" score to prevent them from accidentally ranking #1.
*   **Budget Hard-Cap**: Anything more than 15% over-budget is disqualified to respect your financial constraints.
