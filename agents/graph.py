"""LangGraph-based Agentic Commerce pipeline with conditional routing."""

from __future__ import annotations

from typing import List, Optional, TypedDict, Union

from langgraph.graph import END, StateGraph

from agents.detective import run_detective
from agents.evaluator import run_evaluator
from agents.historian import run_historian
from agents.profiler import run_profiler
from agents.scraper import deduplicate_products, run_scraper
from core.validation import validate_profile


class AgentState(TypedDict):
    user_input: Union[str, dict]
    profile: Optional[dict]
    raw_products: Optional[List[dict]]
    products_with_history: Optional[List[dict]]
    products_with_trust: Optional[List[dict]]
    ranked_products: Optional[List[dict]]
    error: Optional[str]


def node_profiler(state: AgentState) -> dict:
    print("\n[Agent 1: Profiler] Parsing intent...")
    try:
        raw_input = state["user_input"]
        if isinstance(raw_input, dict):
            product_name = raw_input.get("product_name", "")
            budget = raw_input.get("budget", 0)
            specs = raw_input.get("specs", "")
            profile = run_profiler(f"{product_name} under {budget} with {specs}")
            profile["product_type"] = product_name
            profile["budget_inr"] = int(budget) if budget else profile.get("budget_inr")
            profile["raw_specs"] = specs
        else:
            profile = run_profiler(raw_input)

        profile = validate_profile(profile, "graph profiler output")
        print(f"  Product: {profile.get('product_type', 'unknown')}")
        print(f"  Budget : Rs {profile.get('budget_inr', 0) or 0:,}")
        return {"profile": profile, "error": None}
    except Exception as exc:
        return {"error": f"Profiler failed: {exc}"}


def node_scraper(state: AgentState) -> dict:
    print("\n[Agent 2: Scraper] Collecting products...")
    try:
        products = run_scraper(state["profile"] or {})
        if not products:
            return {"error": "No products found."}
        print(f"  Collected: {len(products)}")
        return {"raw_products": products, "error": None}
    except Exception as exc:
        return {"error": f"Scraper failed: {exc}"}


def node_historian(state: AgentState) -> dict:
    print("\n[Agent 3: Historian] Computing price context...")
    try:
        unique_products = deduplicate_products(state.get("raw_products") or [])
        products = run_historian(unique_products)
        return {"products_with_history": products, "error": None}
    except Exception as exc:
        print(f"  Historian degraded: {exc}")
        return {"products_with_history": state.get("raw_products") or [], "error": None}


def node_detective(state: AgentState) -> dict:
    print("\n[Agent 4: Detective] Assessing review trust...")
    try:
        products = run_detective(state.get("products_with_history") or [])
        return {"products_with_trust": products, "error": None}
    except Exception as exc:
        print(f"  Detective degraded: {exc}")
        return {"products_with_trust": state.get("products_with_history") or [], "error": None}


def node_evaluator(state: AgentState) -> dict:
    print("\n[Agent 5: Evaluator] Scoring and ranking...")
    try:
        products = state.get("products_with_trust") or state.get("products_with_history") or []
        ranked = run_evaluator(products, state["profile"] or {})
        print(f"  Ranked: {len(ranked)}")
        return {"ranked_products": ranked, "error": None}
    except Exception as exc:
        return {"error": f"Evaluator failed: {exc}"}


def route_after_profiler(state: AgentState) -> str:
    return "end" if state.get("error") else "scraper"


def route_after_scraper(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    return "historian" if state.get("raw_products") else "end"


def route_after_historian(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    if not state.get("products_with_history"):
        return "end"
    return "detective"


def route_after_detective(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    return "evaluator" if state.get("products_with_trust") else "end"


def build_pipeline():
    graph = StateGraph(AgentState)
    graph.add_node("profiler", node_profiler)
    graph.add_node("scraper", node_scraper)
    graph.add_node("historian", node_historian)
    graph.add_node("detective", node_detective)
    graph.add_node("evaluator", node_evaluator)

    graph.set_entry_point("profiler")
    graph.add_conditional_edges("profiler", route_after_profiler, {"scraper": "scraper", "end": END})
    graph.add_conditional_edges("scraper", route_after_scraper, {"historian": "historian", "end": END})
    graph.add_conditional_edges("historian", route_after_historian, {"detective": "detective", "end": END})
    graph.add_conditional_edges("detective", route_after_detective, {"evaluator": "evaluator", "end": END})
    graph.add_edge("evaluator", END)
    return graph.compile()


def run_pipeline(user_input: Union[str, dict]) -> list[dict]:
    pipeline = build_pipeline()
    initial_state: AgentState = {
        "user_input": user_input,
        "profile": None,
        "raw_products": None,
        "products_with_history": None,
        "products_with_trust": None,
        "ranked_products": None,
        "error": None,
    }
    result = pipeline.invoke(initial_state)
    if result.get("error"):
        raise Exception(result["error"])
    return result.get("ranked_products", [])
