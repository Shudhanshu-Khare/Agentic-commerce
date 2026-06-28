# core/schemas.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any

class UserProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    category: str = Field(description="Product category")
    product_type: str = Field(description="Specific product type")
    budget_inr: Optional[int] = Field(default=None, description="Budget in INR")
    budget_flexibility: float = Field(default=0.10)
    search_keywords: str = ""
    raw_specs: str = ""
    mandatory_specs: Dict[str, str] = Field(default_factory=dict)
    preferred_specs: Dict[str, str] = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)
    use_case: str = Field(default="general")

class Product(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    price: float = 0.0
    rating: float = 0.0
    reviews_count: int = 0
    seller: str = ""
    url: str = ""
    thumbnail: str = ""
    platform: str = ""
    specs: Dict[str, Any] = Field(default_factory=dict)
    price_history_score: float = 0.5
    price_history: Dict[str, Any] = Field(default_factory=dict)
    adjusted_rating: float = 0.0
    trust_score: float = 0.5
    fake_percentage: float = 0.0
    review_red_flags: List[str] = Field(default_factory=list)
    review_verdict: str = "Unknown"
    heuristic_suspicion: float = 0.0
    llm_score: float = 0.0
    llm_weight_used: float = 0.0
    platform_summary: str = "Not available"
    quick_score: float = 0.0
    pre_matched: List[str] = Field(default_factory=list)
    spec_score: float = 0.5
    spec_veto: bool = False
    veto_reason: str = ""
    confirmed_specs: List[str] = Field(default_factory=list)
    missing_specs: List[str] = Field(default_factory=list)
    spec_reasoning: str = ""
    spec_detail: Dict[str, Any] = Field(default_factory=dict)
    scores: Dict[str, float] = Field(default_factory=dict)
    final_score: float = 0.0
    rank: int = 0
    why: List[str] = Field(default_factory=list)

class ReviewData(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str = ""
    rating: int = 5
    verified: bool = True
    date: str = ""
    location: str = ""
    reviewer_name: str = ""

class TrustAnalysis(BaseModel):
    model_config = ConfigDict(extra="allow")

    fake_percentage: float = 0.0
    red_flags: List[str] = Field(default_factory=list)
    adjusted_rating: float = 0.0
    trust_score: float = 0.5
    verdict: str = "Unknown"
    heuristic_score: float = 0.0
    llm_score: float = 0.0
    platform_summary_used: bool = False
