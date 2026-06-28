# agents/profiler.py
import json
import os
import time
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from core.validation import validate_profile

load_dotenv()

PROFILER_PROMPT = """
You are an expert product specification extractor for Indian e-commerce.
Given the user's input, extract the following into strict JSON.
Handle ALL product categories.

{{
  "category": "<electronics|fashion|appliances|consumables|furniture|other>",
  "product_type": "<laptop, phone, shoes, mixer, etc.>",
  "budget_inr": <integer or null>,
  "budget_flexibility": 0.10,
  "search_keywords": "<STRICT: Pick ONLY the top 2 most important specs FROM THE USER'S INPUT. DO NOT add any words, features, or specs that the user did not explicitly mention. Keep it short — max 4-5 words total.>",
  "mandatory_specs": {{}},
  "preferred_specs": {{}},
  "constraints": [],
  "use_case": "<gaming, office, fitness, cooking, etc.>"
}}

CRITICAL RULE for search_keywords:
- ONLY use words that appear in the user's input. NEVER invent or add specs like waterproof, RGB, ANC, etc. unless the user said them.
- Pick the 2 most important specs and write them as a short phrase.
- Example: User says "20 watt speaker, portable" → search_keywords: "20 watt portable"
- Example: User says "10000mAh, fast charging, lightweight" → search_keywords: "10000mAh fast charging"

Return ONLY valid JSON. No markdown. No explanation.
User Input: {user_input}
"""

def run_profiler(user_input: str) -> dict:
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
    prompt = PromptTemplate(input_variables=["user_input"], template=PROFILER_PROMPT)
    chain = prompt | llm

    for attempt in range(3):
        try:
            response = chain.invoke({"user_input": user_input})
            raw = response.content.strip()
            if raw.startswith("```"): raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
            raw = raw.strip()

            brace_count = 0
            end_idx = -1
            for i, ch in enumerate(raw):
                if ch == '{': brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break
            if end_idx > 0: raw = raw[:end_idx + 1]

            parsed = json.loads(raw)
            if "category" not in parsed: parsed["category"] = "other"
            if "product_type" not in parsed: parsed["product_type"] = user_input.split()[0] if user_input else "product"
            return validate_profile(parsed, "profiler output")
        except Exception: time.sleep(1)

    return validate_profile({"category": "other", "product_type": user_input, "budget_inr": None, "budget_flexibility": 0.1, "mandatory_specs": {}, "preferred_specs": {}, "constraints": [], "use_case": "general"}, "profiler fallback")
