# app.py
import asyncio
import os
import sys

import streamlit as st


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


st.set_page_config(
    page_title="Agentic Commerce - AI Product Discovery",
    page_icon="AC",
    layout="wide",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        color: #e5e7eb;
        margin-bottom: 0.2rem;
        line-height: 1.2;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #9ca3af;
        font-weight: 400;
        margin-bottom: 1.5rem;
    }
    .score-number { font-size: 2.35rem; font-weight: 800; line-height: 1; }
    .score-excellent { color: #10b981; }
    .score-good { color: #60a5fa; }
    .score-average { color: #f59e0b; }
    .score-poor { color: #ef4444; }
    .trust-badge { padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; }
    .trust-authentic { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .trust-suspicious { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .trust-highly-suspicious { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .platform-badge { padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
    .platform-amazon { background: rgba(255, 153, 0, 0.15); color: #ff9900; border: 1px solid rgba(255, 153, 0, 0.3); }
    .platform-flipkart { background: rgba(47, 128, 237, 0.15); color: #60a5fa; border: 1px solid rgba(47, 128, 237, 0.3); }
    .custom-divider { height: 1px; background: rgba(148, 163, 184, 0.25); margin: 1.5rem 0; }
</style>
""",
    unsafe_allow_html=True,
)


def format_price(value: float | int | None) -> str:
    return f"Rs {float(value or 0):,.0f}"


def format_terminal_price(value: float | int | None) -> str:
    return f"₹{float(value or 0):,.0f}"


def terminal_log(message: str = "") -> None:
    print(message, flush=True)


def profile_keywords(profile: dict, user_input: dict) -> str:
    keywords = profile.get("search_keywords") or profile.get("raw_specs") or user_input.get("specs", "")
    return str(keywords or "general").strip()


def score_class(score: float) -> str:
    if score >= 75:
        return "score-excellent"
    if score >= 55:
        return "score-good"
    if score >= 40:
        return "score-average"
    return "score-poor"


def trust_class(verdict: str) -> str:
    if verdict == "Authentic":
        return "trust-authentic"
    if verdict == "Suspicious":
        return "trust-suspicious"
    return "trust-highly-suspicious"


def render_funnel(raw_products, unique_products, products_trust, ranked_products, flagged):
    cols = st.columns(5)
    cols[0].metric("Scraped", len(raw_products), "raw candidates")
    cols[1].metric("Unique", len(unique_products), f"-{len(raw_products) - len(unique_products)} duplicates")
    cols[2].metric("Trusted Scan", len(products_trust), f"{flagged} flagged", delta_color="inverse")
    cols[3].metric("Ranked", len(ranked_products), "top matches")
    cols[4].metric("Vetoed", max(len(products_trust) - len(ranked_products), 0), "failed checks", delta_color="inverse")

    st.progress(
        min(1.0, len(ranked_products) / max(len(raw_products), 1)),
        text=f"Pipeline funnel: {len(raw_products)} scraped -> {len(ranked_products)} final recommendations",
    )


def render_timing(timings: dict):
    from core.timing import compute_percentiles

    if not timings:
        return

    st.markdown("#### Agent Latency")
    cols = st.columns(len(timings))
    for idx, (agent, seconds) in enumerate(timings.items()):
        stats = compute_percentiles(agent)
        delta = f"P95 {stats['p95']}s" if stats else "warming up"
        cols[idx].metric(agent.title(), f"{seconds}s", delta)


def run_pipeline_with_progress(user_input: dict) -> dict:
    from agents.detective import run_detective
    from agents.evaluator import run_evaluator
    from agents.historian import run_historian
    from agents.profiler import run_profiler
    from agents.scraper import deduplicate_products, run_scraper
    from core.timing import agent_timer, save_timing
    from core.validation import validate_profile

    timings = {}
    with st.status("Agentic pipeline running...", expanded=True) as status:
        terminal_log("\n🧠 AGENT 1 — PROFILER")
        st.write("Agent 1 - Profiler: understanding your request...")
        with agent_timer("profiler", timings):
            profile = run_profiler(
                f"{user_input['product_name']} under {user_input['budget']} with {user_input['specs']}"
            )
            profile["product_type"] = user_input["product_name"]
            profile["budget_inr"] = int(user_input["budget"]) if user_input["budget"] else profile.get("budget_inr")
            profile["raw_specs"] = user_input["specs"]
            profile = validate_profile(profile, "streamlit profile")
        terminal_log(f"   Category : {profile.get('category', 'other')}")
        terminal_log(f"   Product  : {profile.get('product_type', '')}")
        terminal_log(f"   Budget   : {format_terminal_price(profile.get('budget_inr'))}")
        terminal_log(f"   Keywords : {profile_keywords(profile, user_input)}")
        terminal_log(f"   Time     : {timings['profiler']}s")
        st.write(
            f"Done: {profile.get('product_type')} | Budget: {format_price(profile.get('budget_inr'))} "
            f"({timings['profiler']}s)"
        )

        terminal_log("\n🌐 AGENT 2 — SCRAPER")
        st.write("Agent 2 - Scraper: searching Amazon and Flipkart...")
        with agent_timer("scraper", timings):
            raw_products = run_scraper(profile)
        st.write(f"Done: collected {len(raw_products)} products ({timings['scraper']}s)")

        terminal_log("\n📈 AGENT 3 — HISTORIAN")
        st.write("Agent 3 - Historian: analyzing market and price history...")
        with agent_timer("historian", timings):
            unique_products = deduplicate_products(raw_products)
            products_history = run_historian(unique_products)
        removed = len(raw_products) - len(unique_products)
        historical_count = sum(
            1 for product in products_history if product.get("price_history", {}).get("method") == "historical_30day"
        )
        st.write(
            f"Done: {removed} duplicates removed, {historical_count} products used SQLite history "
            f"({timings['historian']}s)"
        )

        terminal_log("\n🔍 AGENT 4 — DETECTIVE")
        st.write("Agent 4 - Detective: detecting suspicious review patterns...")
        with agent_timer("detective", timings):
            products_trust = run_detective(products_history)
        flagged = sum(1 for product in products_trust if product.get("review_red_flags"))
        llm_checked = sum(1 for product in products_trust if product.get("llm_weight_used", 0) > 0)
        st.write(
            f"Done: {flagged} flagged, {llm_checked} LLM-checked ({timings['detective']}s)"
        )

        terminal_log("\n🏆 AGENT 5 — EVALUATOR")
        st.write("Agent 5 - Evaluator: scoring and ranking...")
        with agent_timer("evaluator", timings):
            ranked_products = run_evaluator(products_trust, profile)
        total_time = round(sum(timings.values()), 2)
        terminal_log(f"\n✅ PIPELINE COMPLETE — {len(ranked_products)} results in {total_time}s\n")
        status.update(
            label=f"Pipeline complete - {len(ranked_products)} products ranked in {total_time}s",
            state="complete",
            expanded=False,
        )

    save_timing(timings)
    return {
        "profile": profile,
        "raw_products": raw_products,
        "unique_products": unique_products,
        "products_trust": products_trust,
        "ranked_products": ranked_products,
        "timings": timings,
        "total_time": total_time,
        "removed": removed,
        "flagged": flagged,
    }


st.markdown('<div class="hero-title">Agentic Commerce</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Multi-agent product intelligence across Amazon.in and Flipkart</div>',
    unsafe_allow_html=True,
)

with st.form("search_form"):
    st.markdown("### Find Your Product")
    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        prod_name = st.text_input("Product Name or Type *", placeholder="e.g., Powerbank, Smartwatch")
        specs = st.text_area("Mandatory Specifications", placeholder="e.g., 10000mAh, 22.5W fast charging", height=68)
    with f_col2:
        budget = st.number_input("Maximum Budget (Rs)", min_value=0, value=0, step=500)
        st.markdown("<br>", unsafe_allow_html=True)
        search_btn = st.form_submit_button("Search Markets", use_container_width=True)

user_input = {"product_name": prod_name, "specs": specs, "budget": budget} if search_btn and prod_name else None
if user_input:
    st.session_state["last_user_input"] = user_input
elif st.session_state.get("last_user_input"):
    user_input = st.session_state["last_user_input"]
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

if user_input:
    from core.cache import get_cached_result, save_cached_result
    from core.logging_config import configure_logging

    logger = configure_logging()
    try:
        payload = get_cached_result(user_input)
        cache_hit = payload is not None
        if cache_hit:
            st.success("Loaded this ranking from the 24-hour local cache.")
            logger.info("cache_hit query=%s", user_input)
        else:
            payload = run_pipeline_with_progress(user_input)
            save_cached_result(user_input, payload)
            logger.info(
                "pipeline_complete query=%s results=%s total_time=%s",
                user_input,
                len(payload["ranked_products"]),
                payload["total_time"],
            )

        profile = payload["profile"]
        raw_products = payload["raw_products"]
        unique_products = payload["unique_products"]
        products_trust = payload["products_trust"]
        ranked_products = payload["ranked_products"]
        timings = payload.get("timings", {})
        total_time = payload.get("total_time", round(sum(timings.values()), 2))
        flagged = payload.get("flagged", sum(1 for product in products_trust if product.get("review_red_flags")))

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Scraped", len(raw_products), "Amazon + Flipkart")
        m2.metric("Duplicates", len(raw_products) - len(unique_products), "removed")
        m3.metric("Flagged", flagged, "review signals", delta_color="inverse")
        m4.metric("Results", len(ranked_products), "top matches")
        m5.metric("Time", f"{total_time}s", "cached" if cache_hit else "end-to-end")

        st.divider()
        render_funnel(raw_products, unique_products, products_trust, ranked_products, flagged)
        render_timing(timings)
        st.divider()

        if not ranked_products:
            budget_val = profile.get("budget_inr", 0) or 0
            if products_trust and budget_val:
                prices = [p.get("price", 0) for p in products_trust if p.get("price", 0) > 0]
                if prices:
                    closest_price = min(prices, key=lambda value: abs(value - budget_val))
                    cheapest = min(prices)
                    diff_pct = ((closest_price - budget_val) / budget_val) * 100
                    direction = "above" if closest_price > budget_val else "below"
                    st.warning(
                        f"No products matched your {format_price(budget_val)} budget after all checks.\n\n"
                        f"- Closest product found: {format_price(closest_price)} ({abs(diff_pct):.0f}% {direction} budget)\n"
                        f"- Cheapest option available: {format_price(cheapest)}\n\n"
                        "Try increasing your budget or broadening your search criteria."
                    )
                else:
                    st.warning("No products were found. Try a different search query.")
            else:
                st.warning("No products matched your requirements after quality and spec checks.")

        for product in ranked_products:
            score = product["final_score"]
            p_class = "platform-amazon" if "amazon" in product["platform"].lower() else "platform-flipkart"
            verdict = product.get("review_verdict", "Unknown")
            budget_val = profile.get("budget_inr", 0) or 0
            budget_label = ""
            if budget_val and product.get("price", 0) > 0:
                pct = ((product["price"] - budget_val) / budget_val) * 100
                if pct <= 0:
                    budget_label = "Within budget"
                elif pct <= 15:
                    budget_label = f"{pct:.0f}% over budget"
                else:
                    budget_label = f"{pct:.0f}% over budget"

            with st.container():
                c1, c2, c3 = st.columns([1.2, 4, 1.6])
                with c1:
                    st.markdown(f"### #{product['rank']}")
                    if product.get("thumbnail"):
                        st.image(product["thumbnail"], width=140)
                with c2:
                    st.markdown(f"#### {product['title'][:100]}")
                    st.markdown(
                        f"**{format_price(product['price'])}** {budget_label} | "
                        f"Rating {product.get('adjusted_rating', product.get('rating', 0)):.1f} | "
                        f'<span class="platform-badge {p_class}">{product["platform"]}</span> '
                        f'<span class="trust-badge {trust_class(verdict)}">{verdict}</span>',
                        unsafe_allow_html=True,
                    )
                    for reason in product.get("why", []):
                        st.markdown(f"- {reason}")
                    if product.get("url"):
                        st.link_button(f"View on {product['platform']}", product["url"])
                with c3:
                    st.markdown(
                        f'<div style="text-align:center"><div class="score-number {score_class(score)}">{score}</div>'
                        '<div style="color:#9ca3af;font-size:0.8rem">Score / 100</div></div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Score Details", expanded=False):
                        for name, value in product.get("scores", {}).items():
                            st.write(f"**{name.replace('_', ' ').title()}:** {int(value * 100)}")
                        hist = product.get("price_history", {})
                        if hist:
                            st.write(f"**Price Method:** {hist.get('method', 'unknown')}")
                        if product.get("llm_weight_used", 0) > 0:
                            st.write(f"**Detective LLM Score:** {product.get('llm_score', 0):.2f}")

            st.divider()

    except Exception as exc:
        st.error(f"Pipeline failed: {exc}")
        st.stop()
else:
    st.markdown(
        """
        <div style="background: rgba(100, 116, 139, 0.08); padding: 1.5rem; border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.2); margin-top: 2rem;">
            <h3 style="color: #e5e7eb; margin-bottom: 0.75rem;">How Agentic Commerce Works</h3>
            <p style="font-size: 1rem; color: #a1a1aa; line-height: 1.55;">
                Enter a product, budget, and must-have specs. The pipeline profiles your intent, scrapes marketplaces,
                analyzes price context, checks review trust, and ranks the strongest product matches.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
