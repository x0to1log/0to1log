from pydantic import BaseModel, Field
from typing import Literal, Optional


class AiAdviseRequest(BaseModel):
    action: Literal["generate", "seo", "review", "factcheck", "deepverify", "conceptcheck", "voicecheck", "retrocheck"]
    post_id: str
    title: str
    content: str
    category: str
    tags: list[str] = []
    excerpt: str = ""
    slug: str = ""
    post_type: str = ""
    guide_items: Optional[dict] = None


class AiAdviseResponse(BaseModel):
    action: str
    success: bool
    result: dict
    model_used: str
    tokens_used: int


# --- Per-action result models (for validation) ---

class GenerateResult(BaseModel):
    guide_items: dict
    focus_items: list[str] = []
    excerpt: str
    tags: list[str]
    slug: str


class SeoResult(BaseModel):
    title_suggestions: list[str]
    tag_recommendations: list[str]
    excerpt_suggestion: str
    seo_notes: str


class ReviewChecklistItem(BaseModel):
    category: str
    status: Literal["pass", "warn", "fail"]
    message: str
    suggestion: str = ""


class ReviewResult(BaseModel):
    checklist: list[ReviewChecklistItem]
    summary: str
    score: int


class FactcheckClaim(BaseModel):
    claim: str
    verdict: Literal["verified", "unverified", "no_source"]
    source: Optional[str] = None
    note: str = ""


class FactcheckResult(BaseModel):
    claims: list[FactcheckClaim]
    broken_links: list[str] = []
    missing_labels: list[str] = []
    overall_confidence: Literal["high", "medium", "low"]


# --- Deep Verify (Tavily-backed fact-check) ---

class VerifiedClaim(BaseModel):
    claim: str
    verdict: Literal["verified", "unverified", "no_source"]
    sources: list[str] = []
    note: str = ""


class BrokenLink(BaseModel):
    url: str
    status_code: int = 0
    error: str = ""


class DeepVerifyResult(BaseModel):
    claims: list[VerifiedClaim]
    broken_links: list[BrokenLink] = []
    overall_confidence: Literal["high", "medium", "low"]
    confidence_reason: str = ""


# --- Category-specific actions ---

class ConceptCheckConcept(BaseModel):
    concept: str
    verdict: Literal["accurate", "unclear", "incorrect"]
    note: str
    suggestion: str = ""


class ConceptCheckResult(BaseModel):
    concepts: list[ConceptCheckConcept]
    missing_concepts: list[str] = []
    depth_assessment: Literal["shallow", "adequate", "thorough"]
    overall_accuracy: Literal["high", "medium", "low"]


class ToneProfile(BaseModel):
    authenticity: int
    specificity: int
    actionability: int


class VoiceCheckSection(BaseModel):
    section: str
    assessment: str
    issue: str = ""
    suggestion: str = ""


class VoiceCheckResult(BaseModel):
    tone_profile: ToneProfile
    sections: list[VoiceCheckSection]
    generic_phrases: list[str] = []
    overall_voice: Literal["authentic", "mixed", "generic"]


class RetroCheckSection(BaseModel):
    section: str
    status: Literal["present", "weak", "missing"]
    note: str
    suggestion: str = ""


class RetroCheckResult(BaseModel):
    sections: list[RetroCheckSection]
    decisions_documented: int
    lessons_extracted: int
    metrics_included: bool
    overall_quality: Literal["publication-ready", "needs-work", "incomplete"]


# --- Handbook AI Advisor ---

class HandbookAdviseRequest(BaseModel):
    action: Literal["related_terms", "translate", "generate"]
    term_id: str
    term: str
    korean_name: str = ""
    categories: list[str] = []
    definition_ko: str = ""
    definition_en: str = ""
    body_basic_ko: str = ""
    body_basic_en: str = ""
    body_advanced_ko: str = ""
    body_advanced_en: str = ""
    force_direction: str = ""  # "ko2en", "en2ko", or "" (auto)


class HandbookAdviseResponse(BaseModel):
    action: str
    success: bool
    result: dict
    model_used: str
    tokens_used: int
    validation_warnings: list[str] = []


class RelatedTermItem(BaseModel):
    term: str
    reason: str
    exists_in_db: bool = False
    slug: str = ""


class RelatedTermsResult(BaseModel):
    related_terms: list[RelatedTermItem]


class TranslateResult(BaseModel):
    definition: str = ""
    body_basic: str = ""
    body_advanced: str = ""
    source_lang: str
    target_lang: str


class GenerateTermResult(BaseModel):
    term_full: str = ""
    korean_name: str = ""
    korean_full: str = ""
    categories: list[str] = []
    definition_ko: str = Field(default="", min_length=80)
    definition_en: str = Field(default="", min_length=80)
    body_basic_ko: str = Field(default="", min_length=2000)
    body_basic_en: str = Field(default="", min_length=2000)
    body_advanced_ko: str = Field(default="", min_length=3000)
    body_advanced_en: str = Field(default="", min_length=3000)


# --- Pipeline Auto-Extract Terms ---

class ExtractedTerm(BaseModel):
    term: str
    korean_name: str = ""
    reason: str = ""


class ExtractTermsResult(BaseModel):
    terms: list[ExtractedTerm]
