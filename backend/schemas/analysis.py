"""Analysis request and response schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RagMatchItem(BaseModel):
    category: Optional[str] = None
    pattern: Optional[str] = None
    score: Optional[float] = None
    evidence: Optional[List[str]] = None


class DomainVerificationOutput(BaseModel):
    status: Optional[str] = None
    assessment: Optional[str] = None
    sender_domain: Optional[str] = None
    expected_domain: Optional[str] = None
    official_domain: Optional[str] = None
    domain_match: Optional[bool] = None
    score_penalty: Optional[int] = None


class SalarySanityOutput(BaseModel):
    status: Optional[str] = None
    assessment: Optional[str] = None
    parsed_salary: Optional[str] = None
    score_penalty: Optional[int] = None


class MlClassifierOutput(BaseModel):
    fraud_probability_pct: Optional[float] = 0.0
    risk_band: Optional[str] = "N/A"
    top_risk_tokens: Optional[List[str]] = []
    top_legit_tokens: Optional[List[str]] = []
    verdict: Optional[str] = None
    ml_fraud_probability: Optional[float] = None


class ToolOutputsResponse(BaseModel):
    rag_matches: Optional[List[Any]] = []
    domain_verification: Optional[Dict[str, Any]] = {}
    salary_sanity: Optional[Dict[str, Any]] = {}
    ml_classifier: Optional[Dict[str, Any]] = {}


class AnalysisResultResponse(BaseModel):
    analysis_id: Optional[str] = None
    email_id: Optional[str] = None
    risk_level: str = "Medium"
    risk_score: int = 50
    explanation: str = ""
    identified_red_flags: List[str] = []
    extracted_data: Dict[str, Any] = {}
    tool_outputs: ToolOutputsResponse = Field(default_factory=ToolOutputsResponse)
    responsible_ai_disclaimer: Optional[str] = None
    execution_mode: Optional[str] = "Advisory Synthesis Engine (Local Mode)"
    scanned_at: Optional[str] = None
    review_status: Optional[str] = "unreviewed"


class AdHocAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Recruitment text to analyze")
    fast_mode: bool = False
    source: Optional[str] = "adhoc_input"
