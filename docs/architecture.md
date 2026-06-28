# Agentic Commerce: System Architecture & Logic

This document provides a comprehensive explanation of how the Agentic Commerce discovery system works, its backend pipeline, and the mathematical logic behind its scoring.

---

## 1. Project Overview
Agentic Commerce is an AI-powered shopping assistant that goes beyond simple keyword matching. It uses a **LangGraph-based autonomous agent pipeline** to search Amazon and Flipkart, analyze review authenticity, track pricing trends, and rank products based on a 7-factor scoring engine tailored to specific product categories.

### Core Architecture
The system is consolidated into four primary files:
- **`app.py`**: The Streamlit frontend dashboard.
- **`agents.py`**: The brains of the 5 autonomous agents and the pipeline orchestrator.
- **`scrapers.py`**: Playwright-based web scrapers for Amazon and Flipkart.
- **`core.py`**: Foundation logic including Schemas, Weights, and Scoring mathematics.

---

## 2. The 5-Agent Pipeline
The system runs a sequential pipeline using **LangGraph** where each agent enriches the product data before passing it to the next.

1.  🧠 **Agent 1: The Profiler**
    - **Task**: Natural Language Understanding (NLU).
    - **Logic**: Uses LLaMA 3.1 (via Groq) to parse the user's search query. It extracts the category, target product, budget, and identifies "Mandatory" vs "Preferred" specifications.
2.  🌐 **Agent 2: The Scraper**
    - **Task**: Real-time Data Collection.
    - **Logic**: Launches Playwright browsers to search `amazon.in` and `flipkart.com`. It bypasses bot detection and collects titles, prices, ratings, and review counts.
3.  📈 **Agent 3: The Historian**
    - **Task**: Market Price Analysis.
    - **Logic**: Analyzes the price distribution of the collected products to find the **Market Median**. It scores each product based on how it compares to its peers (detecting "good deals").
4.  🔍 **Agent 4: The Detective**
    - **Task**: Trust & Fake Review Analysis.
    - **Logic**: Analyzes review patterns (star distribution, verified status, reviewer name patterns) to detect manipulation.
5.  🏆 **Agent 5: The Evaluator**
    - **Task**: Scorer, Ranker, and Explainer.
    - **Logic**: Performs the final LLM-based specification matching and calculates the final weighted score. It generates the human-readable "Why this product?" reasons.

---

## 3. Scoring Mathematics
The final score (0–100) is a weighted sum of 7 individual components:

| Component | Logic / Formula |
| :--- | :--- |
| **Price Score** | `1.0 - ((Price / Median) - 0.5)` |
| **Rating Score** | `Rating / 5.0` (Penalized if fake reviews > 40%) |
| **Popularity Score** | `log1p(Reviews) / log1p(Max Reviews in batch)` |
| **Spec Match** | LLM analysis of product specs vs. user mandatory/preferred requirements. |
| **Price History** | Static score (0.5) scaled by Agent 3's relative price findings. |
| **Seller Trust** | Bonus scores for "Official" stores or platform-shipped items. |
| **Trust Score** | `1.0 - Fake Percentage` (Detected by Detective agent signals). |

---

## 4. Fake Review Detection (The 9 Signals)
The "Detective" agent looks for these red flags to determine the **Trust Score**:
1.  **Unverified Ratio**: High % of reviews from unverified purchases.
2.  **Star Distribution**: Unnatural clusters of 5-star or 1-star reviews.
3.  **Short Reviews**: Excessive "Good product" or "Nice" one-word reviews.
4.  **Date Clustering**: Large bursts of reviews within a few days.
5.  **Location Clustering**: Reviews coming from the same regions for niche items.
6.  **Duplicate Text**: Identical review content across different users.
7.  **Bot Names**: Suspicious pattern-based reviewer names (e.g., "Amazon Customer", "User123").
8.  **Platform Summary**: Comparing the official AI summary against actual user sentiment.
9.  **LLM Linguistic Analysis**: LLaMA 3.1 analyzing if the writing style seems paid or automated.

---

## 5. Dynamic Weighting
Weights change based on the **Product Category** extracted by the Profiler:
- **Electronics**: Prioritizes **Specs (30%)** and **Price (20%)**.
- **Consumables**: Prioritizes **Trust (35%)** and **Seller Reliability (20%)**.
- **Fashion**: Prioritizes **Ratings (35%)** and **Authenticity (25%)**.

---

## 6. Strict Spec Veto System
If a product fails to meet the **Mandatory Specifications** defined by the user (Spec Score < 0.6), it is **vetoed** and removed from the pipeline entirely. It will never appear in the final ranking dashboard.
