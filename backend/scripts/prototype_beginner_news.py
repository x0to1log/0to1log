"""Prototype Beginner persona news from existing published digest rows.

This is an internal experiment script. It reads existing `news_posts` rows,
uses them as the only source material, and writes local preview artifacts.
It does not write back to Supabase.

Usage:
    python -m scripts.prototype_beginner_news --date 2026-05-11 --prompt-only
    python -m scripts.prototype_beginner_news --date 2026-05-11 --type research
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(REPO_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")

from core.config import settings  # noqa: E402
from core.database import get_supabase  # noqa: E402
from services.agents.client import (  # noqa: E402
    build_completion_kwargs,
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
)

DEFAULT_OUTPUT_DIR = REPO_DIR / "output" / "beginner-news"
SUPPORTED_LOCALES = {"en", "ko"}
PROJECT_OR_METHOD_FIRST_RE = re.compile(
    r"^\s*(?:[A-Z][A-Za-z0-9.+_-]{2,}|MoE|LLM|vLLM|ROCm|Transformer|benchmark|"
    r"벤치마크|전문가\s*파라미터|공유\s*풀|라우터|온디바이스)\b"
)
HIGH_RISK_KO_LITERAL_PHRASES = {
    "임베디드 배치": "고객사 상주, 전담 엔지니어 파견, 밀착 도입 지원",
    "현장 임베딩": "고객사 상주, 현장 파견, 밀착 도입 지원",
    "배치 법인": "도입 지원 법인, 현장 구축 지원 조직",
}
ROLLOUT_OR_PROCUREMENT_OVERCLAIMS = {
    "복잡한 조달 없이": "도입 접점이 생겼다 / 파일럿 문의 경로가 명확해졌다",
    "조달 없이": "도입 접점이 생겼다 / 파일럿 문의 경로가 명확해졌다",
    "바로 도입": "검토하거나 문의할 수 있는 경로가 생겼다",
    "즉시 도입": "검토하거나 문의할 수 있는 경로가 생겼다",
}
RESEARCH_ONE_LINE_BLOCKING_JARGON = {
    "MoE": "큰 모델을 더 가볍게 쓰는 설계",
    "전문가 풀": "모델 부품을 나눠 쓰는 방식",
    "전문가 파라미터": "모델 부품",
    "전역 풀": "공유 묶음",
    "루브릭 증류": "채점 기준으로 작은 모델을 가르치는 방법",
    "온정책 증류": "작은 모델을 실제 답변 과정에서 맞추는 방법",
    "리더보드 기반 추천": "과거 평가 기록만 보고 후보를 좁히는 방법",
}
RESEARCH_ONE_LINE_MAX_TECH_TERMS = 2
RESEARCH_ONE_LINE_DENSE_TERMS = {
    "사전학습",
    "토큰",
    "모델 크기",
    "데이터 품질",
    "반복",
    "손실",
    "데이터 레시피",
    "단일 뉴런",
    "뉴런",
    "거절 동작",
    "취약성",
    "스케일링",
    "파라미터",
    "검증 손실",
    "퍼플렉시티",
    "로짓",
    "라우팅",
    "정렬",
    "증류",
    "벤치마크",
}
READER_FACING_BLOCKING_STACK_TERMS = {
    "GB200": "비싼 AI 서버 장비",
    "NVL72": "여러 GPU를 한 묶음으로 쓰는 서버",
    "Slurm": "비싼 장비를 나눠 쓰는 운영 도구",
    "NCCL": "여러 GPU가 계산 결과를 주고받는 통신 계층",
    "NCCL Inspector": "GPU 통신 병목을 보는 도구",
    "CUDA": "GPU에서 모델을 돌리기 위한 소프트웨어 환경",
    "ROCm": "GPU에서 모델을 돌리기 위한 소프트웨어 환경",
    "vLLM": "모델을 빠르게 실행하기 위한 도구",
    "Prometheus": "운영 지표를 모아 보는 시스템",
    "model serving engine": "모델을 빠르게 실행하기 위한 도구",
    "GPU software stack": "GPU에서 모델을 돌리기 위한 소프트웨어 환경",
    "job scheduling software": "비싼 장비를 나눠 쓰는 운영 도구",
    "rack-scale GPU system": "여러 GPU를 한 묶음으로 쓰는 서버",
    "온디바이스": "클라우드에 보내지 않고 기기에서 처리하는 방식",
    "플랫폼 락인": "특정 공급자에 더 의존하게 되는 변화",
    "락인": "특정 공급자에 더 의존하게 되는 변화",
    "작업 스케줄링": "비싼 장비를 나눠 쓰는 방식",
    "집단 통신": "여러 장비가 계산 결과를 주고받는 과정",
    "문서 단위 모듈성": "필요한 부분만 켜서 쓰는 방식",
    "원자료 도구": "원본 데이터를 직접 다루는 도구",
    "희소 모델": "필요한 부분만 켜서 쓰는 모델",
}


RESEARCH_BODY_TECHNICAL_TERM_GROUPS = {
    "moe_routing": {"MoE", "라우팅", "전문가 풀", "전문가 파라미터"},
    "teacher_signal": {"로짓", "루브릭 증류", "온정책 증류"},
    "evaluation_metric": {"퍼플렉시티", "검증 손실", "리더보드 기반 추천"},
    "vector_search": {"임베딩", "벡터", "코퍼스"},
}
RESEARCH_BODY_TECHNICAL_TERMS = {
    term
    for terms in RESEARCH_BODY_TECHNICAL_TERM_GROUPS.values()
    for term in terms
}
RESEARCH_WHAT_CHANGED_BURDEN_CUES = {
    "줄",
    "덜",
    "낮",
    "없이",
    "대신",
    "비용",
    "접근",
    "수작업",
    "데이터",
    "실행",
    "인프라",
    "부담",
    "메모리",
    "지연",
    "시간",
    "권한",
    "후보",
    "좁",
    "가볍",
    "절감",
    "검증",
    "점검",
    "위험",
    "취약",
    "보안",
    "늘",
    "드러",
    "조심",
    "실패",
    "cost",
    "access",
    "manual",
    "data",
    "execution",
    "memory",
    "time",
    "infrastructure",
    "safety",
    "review",
    "verification",
    "risk",
    "check",
    "burden",
    "reduce",
    "reduces",
    "reduced",
    "easier",
    "harder",
    "expose",
    "exposes",
    "exposed",
    "vulnerability",
    "security",
    "fail",
    "failure",
    "deployment",
}
SKIM_WHY_MAX_WORDS = 35
ASCII_STORY_MARKER_RE = re.compile(r"\b[A-Z][A-Za-z0-9.+_-]{2,}\b")
PARENTHETICAL_RE = re.compile(r"[（(]([^）)]{2,})[）)]")
ONE_LINE_READING_INSTRUCTION_PHRASES = {
    "보세요",
    "읽어보세요",
    "오늘 소식을 보",
    "관점으로 보면",
    "중점으로 보자",
    "관점으로 보자",
    "관점에서 보자",
}
ONE_LINE_READING_INSTRUCTION_PATTERNS = {
    "오늘은 ... 보자": re.compile(r"오늘은.{0,80}보자"),
}
SCHEMA_PLACEHOLDER_VALUES = {
    "무슨 일이 있었나",
    "왜 사람들이 신경 쓰나",
    "내 일과 무슨 관련이 있나",
    "테마로 무엇이 변했나",
    "왜 이 문제가 있었나",
    "이번 방법은 무엇을 덜 필요하게 하나",
    "헷갈리지 말 것",
}
GENERIC_STORY_MARKERS = {
    "AI",
    "API",
    "CPU",
    "GPU",
    "JSON",
    "KO",
    "LLM",
    "ML",
    "URL",
}


@dataclass(frozen=True)
class DigestPair:
    batch_date: date
    digest_type: str
    en: dict[str, Any]
    ko: dict[str, Any]


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def slugs_for(batch_date: date, digest_type: str) -> list[str]:
    base_slug = f"{batch_date.isoformat()}-{digest_type}-digest"
    return [base_slug, f"{base_slug}-ko"]


def _normalize_locale(locale: str | None) -> str:
    normalized = str(locale or "ko").strip().lower()
    if normalized not in SUPPORTED_LOCALES:
        raise ValueError(f"Unsupported locale: {locale!r}")
    return normalized


def output_paths(
    output_dir: Path,
    batch_date: date,
    digest_type: str,
    *,
    locale: str = "ko",
) -> dict[str, Path]:
    normalized_locale = _normalize_locale(locale)
    locale_suffix = "" if normalized_locale == "ko" else f"-{normalized_locale}"
    stem = f"{batch_date.isoformat()}-{digest_type}-beginner{locale_suffix}"
    return {
        "json": output_dir / f"{stem}.json",
        "markdown": output_dir / f"{stem}.md",
        "prompt": output_dir / f"{stem}.prompt.txt",
    }


def fetch_digest_pair(supabase: Any, batch_date: date, digest_type: str) -> DigestPair:
    slugs = slugs_for(batch_date, digest_type)
    rows = (
        supabase.table("news_posts")
        .select(
            "slug, locale, title, excerpt, focus_items, source_urls, source_cards, "
            "content_expert, content_learner, quality_score, fact_pack, guide_items, "
            "published_at, status"
        )
        .in_("slug", slugs)
        .execute()
    )
    data = rows.data or []
    en_row = next((r for r in data if r.get("locale") == "en"), None)
    ko_row = next((r for r in data if r.get("locale") == "ko"), None)
    if not en_row or not ko_row:
        raise RuntimeError(
            f"Missing digest rows for {batch_date.isoformat()} {digest_type}: "
            f"en={bool(en_row)} ko={bool(ko_row)} slugs={slugs}"
        )
    return DigestPair(batch_date=batch_date, digest_type=digest_type, en=en_row, ko=ko_row)


def _truncate_text(value: Any, max_chars: int = 12_000) -> str:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...[truncated for prototype prompt]"


def _compact_items(items: Any, max_items: int = 8) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    compacted: list[dict[str, Any]] = []
    allowed_keys = {
        "title",
        "title_ko",
        "headline",
        "summary",
        "excerpt",
        "url",
        "source",
        "persona",
        "score",
        "why_it_matters",
        "category",
    }
    for item in items[:max_items]:
        if isinstance(item, dict):
            compacted.append({k: item[k] for k in allowed_keys if k in item and item[k]})
        else:
            compacted.append({"value": item})
    return compacted


def _source_urls(row: dict[str, Any]) -> list[str]:
    urls = row.get("source_urls") or []
    if urls:
        return [str(url) for url in urls]
    source_cards = row.get("source_cards") or []
    if not isinstance(source_cards, list):
        return []
    seen: dict[str, None] = {}
    for card in source_cards:
        if isinstance(card, dict) and card.get("url"):
            seen.setdefault(str(card["url"]), None)
    return list(seen)


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "slug": row.get("slug"),
        "locale": row.get("locale"),
        "status": row.get("status"),
        "published_at": row.get("published_at"),
        "title": row.get("title"),
        "excerpt": row.get("excerpt"),
        "quality_score": row.get("quality_score"),
        "source_urls": _source_urls(row),
        "focus_items": _compact_items(row.get("focus_items"), max_items=10),
        "guide_items": _compact_items(row.get("guide_items"), max_items=10),
        "source_cards": _compact_items(row.get("source_cards"), max_items=10),
        "content_expert": _truncate_text(row.get("content_expert")),
        "content_learner": _truncate_text(row.get("content_learner")),
    }


def _digest_type_rules(digest_type: str, *, locale: str = "ko") -> str:
    normalized_locale = _normalize_locale(locale)
    if normalized_locale == "en" and digest_type == "business":
        return """
Business Beginner format:
- Business Beginner main_items: 2-3.
- Goal: make a true beginner understand why the business/tool/vendor/market story matters.
- Business one_line is a lens sentence, not a catalog. It should answer: "what business change should I notice today?"
- Do not list vendor, product, equipment, or project names in business one_line; put concrete names and examples in main_items instead.
- Do not write reading instructions like "look at this through..." or "today we should focus on...". State the business change directly.
- If a product page only says request access, request a scan, or contact sales, say an adoption touchpoint or pilot inquiry path appeared. Do not infer immediate adoption or simplified procurement.
- Main items must explain: what happened, why people care, why it matters at work, and the likely misconception.
- Prefer practical consequences: product choice, workflow change, budget/vendor signal, adoption timing, user trust.
- Avoid overclaiming market impact from one secondary source or one leaderboard/ranking.
"""
    if normalized_locale == "en" and digest_type == "research":
        return """
Research Beginner format:
- Research Beginner main_items: 1-2. Default to 2 only if both items are easy to explain under one simple theme. Do not use 3 main_items for research.
- Goal: make a true beginner understand the direction of the technical change without pretending they know ML papers.
- Main items must explain: the change in one sentence, why the problem existed, what got easier or what needs more care, and the likely misconception.
- Prefer capability shifts, evaluation limits, and why the research problem exists.
- Research main item body may use at most 2 technical method terms before dont_confuse or next_read.
- Research one_line should use at most 2 technical terms. Give the plain consequence before adding more detail.
- For Research one_line, write one shared plain consequence sentence: do not summarize two mechanisms or two papers in the same one_line.
- what_changed must answer which burden is reduced or which new risk/check burden is exposed: cost, access, manual work, data, execution, memory, time, infrastructure, safety review, or deployment verification.
- Avoid turning method names into a glossary. The frontend handbook handles term definitions.
"""
    if digest_type == "business":
        return """
Business Beginner format:
- Business Beginner main_items: 2-3 (메인 2-3개).
- Goal: make a true beginner understand why the business/tool/vendor/market story matters.
- Business one_line is a lens sentence, not a catalog. It should answer:
  "오늘 비즈니스 뉴스를 어떤 관점으로 보면 되나?"
- Do not list vendor, product, equipment, or project names in business one_line;
  put concrete names and examples in main_items instead.
- Do not write reading instructions like 보세요, 오늘은 ... 보자, or 중점으로 보자. State the lens as article copy.
- If a product page only says request access, request a scan, or contact sales, say 도입 접점 or
  파일럿 문의 경로가 생겼다. Do not infer 복잡한 조달 없이, 바로 도입, or 즉시 도입.
- Main items must use these lenses: "무슨 일이 있었나", "왜 사람들이 신경 쓰나", "내 일과 무슨 관련이 있나", "헷갈리지 말 것".
- Prefer practical consequences: product choice, workflow change, budget/vendor signal, adoption timing, user trust.
- Avoid overclaiming market impact from one secondary source or one leaderboard/ranking.
"""
    if digest_type == "research":
        return """
Research Beginner format:
- Research Beginner main_items: 1-2. Default to 2 only if both items are easy to explain under one simple theme. Do not use 3 main_items for research.
- Goal: make a true beginner understand the direction of the technical change without pretending they know ML papers.
- Main items must use these lenses: "한마디로 무슨 변화인가", "왜 이 문제가 있었나", "무엇이 쉬워졌나 또는 무엇을 더 조심해야 하나", "헷갈리지 말 것".
- Prefer capability shifts, evaluation limits, and why the research problem exists.
- Research main item body may use at most 2 technical method terms before dont_confuse or next_read.
- Research one_line should use at most 2 technical terms. Give the plain consequence before adding more detail.
- For Research one_line, write one shared plain consequence sentence: do not summarize two mechanisms or two papers in the same one_line.
- what_changed must answer which burden is reduced or which new risk/check burden is exposed: cost, access, manual work, data, execution, memory, time, infrastructure, safety review, or deployment verification.
- Avoid turning method names into a glossary. The frontend handbook handles term definitions.
"""
    raise ValueError(f"Unsupported digest_type: {digest_type!r}")


def _schema_block(digest_type: str, *, locale: str = "ko") -> str:
    normalized_locale = _normalize_locale(locale)
    if normalized_locale == "en" and digest_type == "business":
        return """
{
  "headline": "short English preview title",
  "one_line": "one sentence summary for a true beginner",
  "background": ["2-4 short context bullets"],
  "main_items": [
    {
      "title": "beginner-friendly item title",
      "what_happened": "plain-language description",
      "why_people_care": "why this matters",
      "business_relevance": "why this matters for work, buying, operations, or product decisions",
      "dont_confuse": "the likely misconception to avoid",
      "next_read": "which learner-digest section to read next"
    }
  ],
  "skim_items": [
    {
      "title": "lower-priority story",
      "why_skim": "why it is enough to skim today; 35 English words or fewer"
    }
  ],
  "context": ["optional broader pattern bullets"],
  "next_reads": [
    {
      "label": "Learner news next read",
      "target": "specific learner/expert title or section",
      "reason": "why this is the next step"
    }
  ],
  "quality_notes": ["internal notes about tradeoffs or weak source areas"]
}
""".strip()
    if normalized_locale == "en" and digest_type == "research":
        return """
{
  "headline": "short English preview title",
  "one_line": "one sentence summary for a true beginner",
  "background": ["2-4 short context bullets"],
  "main_items": [
    {
      "title": "beginner-friendly item title",
      "what_happened": "plain-language description",
      "why_people_care": "why this matters",
      "research_problem": "what problem existed",
      "what_changed": "what got easier or what needs more care",
      "dont_confuse": "the likely misconception to avoid",
      "next_read": "which learner-digest section to read next"
    }
  ],
  "skim_items": [
    {
      "title": "lower-priority story",
      "why_skim": "why it is enough to skim today; 35 English words or fewer"
    }
  ],
  "context": ["optional broader pattern bullets"],
  "next_reads": [
    {
      "label": "Learner news next read",
      "target": "specific learner/expert title or section",
      "reason": "why this is the next step"
    }
  ],
  "quality_notes": ["internal notes about tradeoffs or weak source areas"]
}
""".strip()
    if digest_type == "business":
        return """
{
  "headline": "short Korean preview title",
  "one_line": "one lens sentence for a true beginner; not a catalog",
  "background": ["2-4 short context bullets"],
  "main_items": [
    {
      "title": "beginner-friendly item title",
      "what_happened": "plain-language description",
      "why_people_care": "why this matters",
      "business_relevance": "내 일과 무슨 관련이 있나",
      "dont_confuse": "헷갈리지 말 것",
      "next_read": "which learner-digest section to read next"
    }
  ],
  "skim_items": [
    {
      "title": "lower-priority story",
      "why_skim": "why it is enough to skim today; 35 Korean words or fewer"
    }
  ],
  "context": ["optional broader pattern bullets"],
  "next_reads": [
    {
      "label": "학습자 뉴스 이어읽기",
      "target": "specific learner/expert title or section",
      "reason": "why this is the next step"
    }
  ],
  "quality_notes": ["internal notes about tradeoffs or weak source areas"]
}
""".strip()
    if digest_type == "research":
        return """
{
  "headline": "short Korean preview title",
  "one_line": "one sentence summary for a true beginner",
  "background": ["2-4 short context bullets"],
  "main_items": [
    {
      "title": "beginner-friendly item title",
      "what_happened": "plain-language description",
      "why_people_care": "why this matters",
      "research_problem": "왜 이 문제가 있었나",
      "what_changed": "무엇이 쉬워졌나 또는 무엇을 더 조심해야 하나",
      "dont_confuse": "헷갈리지 말 것",
      "next_read": "which learner-digest section to read next"
    }
  ],
  "skim_items": [
    {
      "title": "lower-priority story",
      "why_skim": "why it is enough to skim today; 35 Korean words or fewer"
    }
  ],
  "context": ["optional broader pattern bullets"],
  "next_reads": [
    {
      "label": "학습자 뉴스 이어읽기",
      "target": "specific learner/expert title or section",
      "reason": "why this is the next step"
    }
  ],
  "quality_notes": ["internal notes about tradeoffs or weak source areas"]
}
""".strip()
    raise ValueError(f"Unsupported digest_type: {digest_type!r}")


def build_beginner_prompt(pair: DigestPair, *, locale: str = "ko") -> str:
    normalized_locale = _normalize_locale(locale)
    output_language = "English" if normalized_locale == "en" else "Korean"
    skim_word_language = "English" if normalized_locale == "en" else "Korean"
    locale_source_rule = (
        "Use the English digest row as the primary source. Use the Korean row only to cross-check context if helpful."
        if normalized_locale == "en"
        else "Use the Korean digest row as the primary source. Use the English row only to cross-check context if helpful."
    )
    source = {
        "date": pair.batch_date.isoformat(),
        "digest_type": pair.digest_type,
        "target_locale": normalized_locale,
        "english_digest_row": _compact_row(pair.en),
        "korean_digest_row": _compact_row(pair.ko),
    }
    source_json = json.dumps(source, ensure_ascii=False, indent=2, default=str)
    return f"""
You are prototyping a new "Beginner" persona digest for 0to1log.

Use ONLY the source digest rows below. Do not browse. Do not invent new claims,
numbers, sources, rankings, benchmarks, dates, or company positions.

Output language: {output_language}.
{locale_source_rule}

Core product decision:
- This is not a glossary format. 용어 정의를 길게 반복하지 마세요.
- Unknown terms will be clickable in the frontend handbook, so explain context and confusion risk instead.
- Do not cover every story deeply. 모든 소식을 깊게 다루지 마세요.
- Select main_items by digest type: Research 1-2, Business 2-3. These are the stories a true beginner should actually understand today.
- The one_line may summarize only selected main_items. Do not mention skim_items or non-main stories in one_line.
- For Business, one_line is a lens sentence, not a catalog. Do not list vendor, product,
  equipment, or project names there; put concrete names and examples in main_items instead.
- Put lower-priority items under "가볍게 지나가도 되는 소식".
- Keep skim_items light: each skim_items.why_skim must be 35 {skim_word_language} words or fewer.
- Include a "학습자 뉴스 이어읽기 경로" so a beginner can attempt the learner digest next.
- Every main item needs "헷갈리지 말 것" to prevent the most likely misconception.
- Keep claims traceable to the existing expert/learner digest text or source URLs.
- Write short but not shallow explanations. For main item fields, use one setup sentence and one consequence sentence when a true beginner needs the extra step.
- In the one-line summary, explain the meaning of the change before naming projects or methods:
  프로젝트명보다 변화의 의미를 먼저 말하세요.
- Do not start headline, one_line, and main item titles with a project, paper, method, benchmark,
  model, or framework name. Start with the practical/research direction first, then mention names
  in parentheses or later in the sentence.
- Meaning-first examples:
  - Bad: "ActCam은 추가 학습 없이 카메라와 동작을 제어한다."
  - Good: "영상 AI가 추가 학습을 줄이면서 카메라와 동작을 더 세밀하게 제어하려 한다 (ActCam)."
  - Bad: "Hermes Agent v0.13 adds Tenacity."
  - Good: "반복 업무를 이어서 처리하는 에이전트 업데이트가 실사용 신호를 받고 있다 (Hermes Agent v0.13)."
- Surface-change-first rule for reader-facing fields: headline, one_line, and main item titles
  must start from the change a beginner can feel or understand: cost, access, workflow, security,
  evaluation burden, vendor dependence, deployment risk, or operating complexity.
- Do not put infrastructure stack names in reader-facing fields. Avoid names such as GB200, NVL72,
  Slurm, NCCL, CUDA, ROCm, vLLM, Prometheus, and similar implementation details there. Put them in
  what_happened or next_read only when needed as evidence.
- Replace abstract infrastructure phrasing with the user-visible effect:
  "작업 스케줄링" -> "비싼 장비를 나눠 쓰는 방식";
  "집단 통신" -> "여러 장비가 계산 결과를 주고받는 과정";
  "플랫폼 락인" -> "특정 공급자에 더 의존하게 되는 변화";
  "ROCm" -> "GPU에서 모델을 돌리기 위한 소프트웨어 환경";
  "vLLM" -> "모델을 빠르게 실행하기 위한 도구".
- Do not stack jargon. A beginner should understand the first sentence even if they do not know model,
  benchmark, MoE, agent, routing, or inference yet.
- Research one_line must use everyday substitutes before terms. Do not put MoE, 전문가 풀,
  전문가 파라미터, 전역 풀, 루브릭 증류, 온정책 증류, or 리더보드 기반 추천 in the one_line.
  Put method names like ROPD, ActCam, UniPool, or ModelLens in parentheses only after the plain meaning.
- Research one_line should use at most 2 technical terms. Give the plain consequence before adding more detail.
- For Research one_line, write one shared plain consequence sentence: do not summarize two mechanisms or two papers in the same one_line.
  Bad: "사전학습에서 토큰·모델 크기·데이터 품질·반복이 손실에 미치는 영향을 예측한다."
  Good: "학습 데이터를 고르는 일을 덜 감으로 하게 해주는 연구가 나왔다."
- Business one_line must not be meta guidance. Avoid "오늘은 ... 보자", "중점으로 보자",
  "관점으로 보자", and "관점으로 보면". Say the business change directly.
- For enterprise access, prefer calibrated wording such as "도입 접점이 생겼다" or
  "파일럿 문의 경로가 명확해졌다". Do not write "복잡한 조달 없이", "바로 도입",
  or "즉시 도입" unless the source explicitly says so.
- Never expose internal field names in the output. 내부 필드명 such as content_learner,
  content_expert, guide_items, source_cards, or JSON path names must not appear.
- Never copy schema labels as field content. Values such as "왜 이 문제가 있었나",
  "무엇이 쉬워졌나 또는 무엇을 더 조심해야 하나", "이번 방법은 무엇을 덜 필요하게 하나",
  or "헷갈리지 말 것" are section labels,
  not valid answers. Each field must contain the actual explanation.
- Avoid high-risk literal translations. In enterprise go-to-market or support context,
  do not write "임베디드 배치", "현장 임베딩", or "배치 법인"; use "고객사 상주",
  "전담 엔지니어 파견", "밀착 도입 지원", or "도입 지원 법인".

{_digest_type_rules(pair.digest_type, locale=normalized_locale)}

Return strict JSON with this shape:
{_schema_block(pair.digest_type, locale=normalized_locale)}

Validation rules:
- Research main_items length must be 1 or 2. Do not use 3 main_items for research.
- Business main_items length must be 2 or 3.
- skim_items length must be 0 to 4.
- one_line may summarize only selected main_items. Do not mention skim_items or non-main stories in one_line.
- Business one_line must be a lens sentence, not a catalog/list of concrete examples.
- Each skim_items.why_skim must be 35 {skim_word_language} words or fewer.
- Prefer short but not shallow paragraphs over long explanations.
- Avoid "AI 시대가 온다" style generic phrasing.
- Do not include a separate glossary or term-definition section.
- If a metric/ranking/date is mutable, include attribution and an absolute date.

SOURCE DIGEST ROWS:
{source_json}
""".strip()


def _story_markers(value: Any) -> set[str]:
    text = str(value or "")
    markers = {
        token
        for token in ASCII_STORY_MARKER_RE.findall(text)
        if token not in GENERIC_STORY_MARKERS
    }
    if "수학" in text and "워크벤치" in text:
        markers.add("수학 워크벤치")
    if "에이전트" in text:
        markers.add("에이전트")
    return markers


def _item_story_markers(items: Any, keys: tuple[str, ...]) -> set[str]:
    if not isinstance(items, list):
        return set()
    markers: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            for key in keys:
                markers.update(_story_markers(item.get(key)))
    return markers


def _research_body_technical_terms(item: dict[str, Any]) -> list[str]:
    fields = ("title", "what_happened", "why_people_care", "research_problem", "what_changed")
    text = "\n".join(str(item.get(field) or "") for field in fields)
    matched_groups: list[str] = []
    for group_name, terms in RESEARCH_BODY_TECHNICAL_TERM_GROUPS.items():
        hits = sorted(term for term in terms if term in text)
        if hits:
            matched_groups.append(f"{group_name}: {', '.join(hits)}")
    return matched_groups


def _word_count(value: Any) -> int:
    return len(str(value or "").split())


def _business_one_line_catalog_issues(value: Any) -> list[str]:
    text = str(value or "")
    parentheticals = [match.group(1).strip() for match in PARENTHETICAL_RE.finditer(text)]
    issues: list[str] = []
    if len(parentheticals) >= 2:
        issues.append("multiple parenthetical examples")
    long_or_list_like = [
        item
        for item in parentheticals
        if len(item) > 40 or "," in item or "·" in item
    ]
    if long_or_list_like:
        issues.append(f"catalog-like parenthetical detail: {long_or_list_like[:2]}")
    return issues


def _one_line_reading_instruction_issues(value: Any) -> list[str]:
    text = str(value or "")
    phrase_issues = {
        phrase for phrase in ONE_LINE_READING_INSTRUCTION_PHRASES if phrase in text
    }
    pattern_issues = {
        label
        for label, pattern in ONE_LINE_READING_INSTRUCTION_PATTERNS.items()
        if pattern.search(text)
    }
    return sorted(phrase_issues | pattern_issues)


def _research_one_line_density_issues(value: Any) -> list[str]:
    text = str(value or "")
    matches = sorted(
        {term for term in RESEARCH_ONE_LINE_DENSE_TERMS if term in text},
        key=lambda term: (-len(term), term),
    )
    if len(matches) <= RESEARCH_ONE_LINE_MAX_TECH_TERMS:
        return []
    return matches


def _rollout_or_procurement_overclaim_issues(payload: dict[str, Any]) -> list[str]:
    fields: list[tuple[str, Any]] = [
        ("headline", payload.get("headline")),
        ("one_line", payload.get("one_line")),
        ("background", payload.get("background")),
        ("context", payload.get("context")),
    ]
    for index, item in enumerate(payload.get("main_items") or [], start=1):
        if not isinstance(item, dict):
            continue
        for key in ("title", "what_happened", "why_people_care", "business_relevance"):
            fields.append((f"main_items[{index}].{key}", item.get(key)))
    for index, item in enumerate(payload.get("skim_items") or [], start=1):
        if isinstance(item, dict):
            fields.append((f"skim_items[{index}].why_skim", item.get("why_skim")))

    issues: list[str] = []
    for field_name, value in fields:
        values = value if isinstance(value, list) else [value]
        for item_value in values:
            text = str(item_value or "")
            if "뜻은 아니다" in text or "의미는 아니다" in text:
                continue
            hits = [phrase for phrase in ROLLOUT_OR_PROCUREMENT_OVERCLAIMS if phrase in text]
            if hits:
                replacements = {
                    phrase: ROLLOUT_OR_PROCUREMENT_OVERCLAIMS[phrase]
                    for phrase in hits
                }
                issues.append(f"{field_name}: {replacements}")
    return issues


def _find_schema_placeholders(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    main_items = payload.get("main_items") or []
    if not isinstance(main_items, list):
        return issues
    for index, item in enumerate(main_items, start=1):
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if isinstance(value, str) and value.strip() in SCHEMA_PLACEHOLDER_VALUES:
                issues.append(f"main_items[{index}].{key}={value!r}")
    return issues


def validate_beginner_payload(
    payload: dict[str, Any],
    digest_type: str,
    *,
    locale: str = "ko",
) -> None:
    normalized_locale = _normalize_locale(locale)
    required_top = ["headline", "one_line", "background", "main_items", "skim_items", "next_reads"]
    missing_top = [key for key in required_top if key not in payload]
    if missing_top:
        raise ValueError(f"Missing top-level keys: {missing_top}")

    main_items = payload.get("main_items")
    if not isinstance(main_items, list):
        raise ValueError("main_items must be a list")
    if digest_type == "research":
        if not 1 <= len(main_items) <= 2:
            raise ValueError("research main_items must contain 1-2 items")
    elif digest_type == "business":
        if not 2 <= len(main_items) <= 3:
            raise ValueError("business main_items must contain 2-3 items")
    else:
        raise ValueError(f"Unsupported digest_type: {digest_type!r}")

    skim_items = payload.get("skim_items")
    if not isinstance(skim_items, list) or len(skim_items) > 4:
        raise ValueError("skim_items must contain 0-4 items")
    for index, item in enumerate(skim_items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"skim_items[{index}] must be an object")
        if _word_count(item.get("why_skim")) > SKIM_WHY_MAX_WORDS:
            raise ValueError(
                f"skim_items[{index}].why_skim must be {SKIM_WHY_MAX_WORDS} Korean words or fewer"
            )

    serialized = json.dumps(payload, ensure_ascii=False)
    forbidden_internal_names = [
        "content_learner",
        "content_expert",
        "guide_items",
        "source_cards",
        "focus_items",
    ]
    leaked_names = [name for name in forbidden_internal_names if name in serialized]
    if leaked_names:
        raise ValueError(f"Output leaked internal field names: {leaked_names}")

    leaked_literal_phrases = [
        phrase for phrase in HIGH_RISK_KO_LITERAL_PHRASES if phrase in serialized
    ]
    if leaked_literal_phrases:
        replacements = {
            phrase: HIGH_RISK_KO_LITERAL_PHRASES[phrase]
            for phrase in leaked_literal_phrases
        }
        raise ValueError(
            f"Output contains high-risk literal translation: {replacements}"
        )

    schema_placeholder_issues = _find_schema_placeholders(payload)
    if schema_placeholder_issues:
        raise ValueError(
            "Output contains schema placeholder labels instead of content: "
            + " | ".join(schema_placeholder_issues)
        )

    reading_instruction_issues = _one_line_reading_instruction_issues(payload.get("one_line"))
    if reading_instruction_issues:
        raise ValueError(
            "one_line must state the lens as article copy, not instruct the reader; "
            f"remove phrases={reading_instruction_issues}"
        )

    if digest_type == "business":
        rollout_overclaim_issues = _rollout_or_procurement_overclaim_issues(payload)
        if rollout_overclaim_issues:
            raise ValueError(
                "Output overclaims rollout or procurement speed; "
                + " | ".join(rollout_overclaim_issues)
            )
        catalog_issues = _business_one_line_catalog_issues(payload.get("one_line"))
        if catalog_issues:
            raise ValueError(
                "business one_line must be a lens sentence, not a catalog/list; "
                f"issues={catalog_issues}"
            )

    reader_facing_fields = [
        ("headline", payload.get("headline")),
        ("one_line", payload.get("one_line")),
    ]
    for index, item in enumerate(main_items, start=1):
        if isinstance(item, dict):
            reader_facing_fields.append((f"main_items[{index}].title", item.get("title")))

    surface_change_issues: list[str] = []
    for field_name, value in reader_facing_fields:
        if not isinstance(value, str):
            continue
        blocking_terms = [
            term for term in READER_FACING_BLOCKING_STACK_TERMS if term in value
        ]
        if blocking_terms:
            replacements = {
                term: READER_FACING_BLOCKING_STACK_TERMS[term]
                for term in blocking_terms
            }
            surface_change_issues.append(
                f"{field_name}: {replacements}"
            )
    if surface_change_issues:
        raise ValueError(
            "reader-facing fields must be surface-change-first; "
            "remove stack or abstract terms: "
            + " | ".join(surface_change_issues)
        )

    one_line_markers = _story_markers(payload.get("one_line"))
    main_markers = _item_story_markers(
        main_items,
        (
            "title",
            "what_happened",
            "why_people_care",
            "business_relevance",
            "research_problem",
            "what_changed",
        ),
    )
    skim_markers = _item_story_markers(skim_items, ("title",))
    non_main_markers = sorted((skim_markers - main_markers) & one_line_markers)
    if non_main_markers:
        raise ValueError(
            "one_line must summarize only selected main_items; "
            f"remove skim_items or non-main story markers: {non_main_markers}"
        )

    if digest_type == "research":
        one_line = str(payload.get("one_line") or "")
        blocking_terms = [
            term for term in RESEARCH_ONE_LINE_BLOCKING_JARGON if term in one_line
        ]
        if blocking_terms:
            replacements = {
                term: RESEARCH_ONE_LINE_BLOCKING_JARGON[term]
                for term in blocking_terms
            }
            raise ValueError(
                f"research one_line contains beginner-blocking jargon: {replacements}"
            )
        density_terms = _research_one_line_density_issues(one_line)
        if density_terms:
            raise ValueError(
                "research one_line is too dense for a true beginner; "
                f"use a plain consequence before method detail; terms={density_terms}"
            )

    for field_name, value in reader_facing_fields:
        if (
            normalized_locale == "ko"
            and isinstance(value, str)
            and PROJECT_OR_METHOD_FIRST_RE.search(value)
        ):
            raise ValueError(
                f"{field_name} must be meaning-first; "
                f"do not start with project or method names; value={value[:100]!r}"
            )

    common_required = ["title", "why_people_care", "dont_confuse", "next_read"]
    if digest_type == "business":
        item_required = common_required + ["what_happened", "business_relevance"]
    elif digest_type == "research":
        item_required = common_required + ["research_problem", "what_changed"]
    else:
        raise ValueError(f"Unsupported digest_type: {digest_type!r}")

    for index, item in enumerate(main_items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"main_items[{index}] must be an object")
        missing_item = [key for key in item_required if not item.get(key)]
        if missing_item:
            raise ValueError(f"main_items[{index}] missing keys: {missing_item}")
        if digest_type == "research":
            technical_terms = _research_body_technical_terms(item)
            if len(technical_terms) > 2:
                raise ValueError(
                    f"research main_items[{index}] technical term density too high: {technical_terms}"
                )
            what_changed = str(item.get("what_changed") or "")
            what_changed_search = what_changed.lower() if normalized_locale == "en" else what_changed
            if not any(cue in what_changed_search for cue in RESEARCH_WHAT_CHANGED_BURDEN_CUES):
                raise ValueError(
                    f"research main_items[{index}].what_changed must explain which burden changes"
                )


def build_revision_prompt(
    payload: dict[str, Any],
    validation_error: str,
    *,
    locale: str = "ko",
) -> str:
    normalized_locale = _normalize_locale(locale)
    output_language = "English" if normalized_locale == "en" else "Korean"
    skim_word_language = "English" if normalized_locale == "en" else "Korean"
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return f"""
Your previous JSON failed validation:
{validation_error}

Revise the fields needed to satisfy the validation rule, then re-check every validation rule before returning.
- Return the full corrected JSON, not a patch.
- Output language: {output_language}.
- Keep the same schema and factual content.
- For headline, one_line, and main item titles: do not start with project or method names.
- Start with the practical or research meaning first, then put project/model/framework names later.
- Surface-change-first: reader-facing fields must start from cost, access, workflow, security,
  evaluation burden, vendor dependence, deployment risk, or operating complexity.
- Do not put infrastructure stack names in reader-facing fields; move names like GB200, NVL72,
  Slurm, NCCL, CUDA, ROCm, vLLM, or Prometheus into body evidence only.
- Replace "온디바이스" -> "클라우드에 보내지 않고 기기에서 처리하는 방식" in reader-facing fields.
- If the validation error includes a replacement map, apply it literally.
- Replacement examples:
  "작업 스케줄링" -> "비싼 장비를 나눠 쓰는 방식";
  "집단 통신" -> "여러 장비가 계산 결과를 주고받는 과정";
  "플랫폼 락인" -> "특정 공급자에 더 의존하게 되는 변화".
- Research outputs must use 1-2 main_items. Do not use 3 main_items for research.
- Business outputs must use 2-3 main_items.
- one_line may summarize only selected main_items. Do not mention skim_items or non-main stories in one_line.
- Business one_line must be a lens sentence, not a catalog/list. Do not list vendor, product,
  equipment, or project names there; put concrete names and examples in main_items instead.
- Business one_line should usually contain zero parentheses. If it has a parenthetical list, remove it and keep only the shared business lens.
- Do not write reading instructions like 보세요 or 읽어보세요 in one_line. State the lens as article copy.
- Never copy schema labels as content. Replace labels like "왜 이 문제가 있었나",
  "이번 방법은 무엇을 덜 필요하게 하나", or "헷갈리지 말 것" with concrete explanations.
- Each skim_items.why_skim must be 35 {skim_word_language} words or fewer.
- Research main item body may use at most 2 technical method terms before dont_confuse or next_read.
- Research what_changed must explain which burden is reduced or which new risk/check burden is exposed: cost, access, manual work, data, execution, memory, time, infrastructure, safety review, or deployment verification.
- Research one_line should use at most 2 technical terms and state the plain consequence before adding more detail.
- If the validation error says research one_line is too dense, keep at most one term from the reported terms list, write one shared plain consequence, and do not summarize two mechanisms or two papers in the same one_line.
- A research one_line must not contain MoE, 전문가 풀, 전문가 파라미터, 전역 풀,
  루브릭 증류, 온정책 증류, or 리더보드 기반 추천. Use plain substitutes first.
- Business one_line must not use meta reading guidance such as 오늘은 ... 보자, 중점으로 보자,
  관점으로 보자, or 관점으로 보면.
- For enterprise access, use 도입 접점 or 파일럿 문의 경로 instead of 복잡한 조달 없이,
  바로 도입, or 즉시 도입 unless the source explicitly says so.
- Do not add new claims or sources.

Previous JSON:
{payload_json}
""".strip()


def _bullet_lines(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [f"- {item}" for item in items if item]


def render_article_markdown(
    payload: dict[str, Any],
    digest_type: str,
    *,
    locale: str = "ko",
) -> str:
    normalized_locale = _normalize_locale(locale)
    if normalized_locale == "en":
        main_heading = (
            "What To Understand Today"
            if digest_type == "business"
            else "Research To Understand Today"
        )
        lines = [
            "## Today's Key Point",
            "",
            str(payload.get("one_line") or ""),
            "",
            "## Context First",
            "",
        ]
        lines.extend(_bullet_lines(payload.get("background")))
        lines.extend(["", f"## {main_heading}", ""])

        main_items = payload.get("main_items") or []
        for index, item in enumerate(main_items, start=1):
            if not isinstance(item, dict):
                continue
            lines.extend([f"### {index}. {item.get('title', '').strip()}", ""])
            if item.get("what_happened"):
                lines.extend(["**What Happened**", "", str(item["what_happened"]), ""])
            if item.get("research_problem"):
                lines.extend(["**What Problem Was This Solving?**", "", str(item["research_problem"]), ""])
            if item.get("what_changed"):
                lines.extend(["**What Got Easier / What Needs More Care**", "", str(item["what_changed"]), ""])
            if item.get("why_people_care"):
                lines.extend(["**Why People Care**", "", str(item["why_people_care"]), ""])
            if item.get("business_relevance"):
                lines.extend(["**Why It Matters At Work**", "", str(item["business_relevance"]), ""])
            if item.get("dont_confuse"):
                lines.extend(["**Don't Confuse This With**", "", str(item["dont_confuse"]), ""])
            if item.get("next_read"):
                lines.extend(["**Next Learner News To Read**", "", str(item["next_read"]), ""])

        lines.extend(["## Worth Skimming Today", ""])
        skim_items = payload.get("skim_items") or []
        if skim_items:
            for item in skim_items:
                if isinstance(item, dict):
                    title = str(item.get("title") or "").strip()
                    why_skim = str(item.get("why_skim") or "").strip()
                    if title and why_skim:
                        lines.append(f"- **{title}**: {why_skim}")
                    elif title:
                        lines.append(f"- {title}")
                elif item:
                    lines.append(f"- {item}")
        else:
            lines.append("- None")

        context_items = payload.get("context") or []
        if context_items:
            lines.extend(["", "## Today's Pattern", ""])
            lines.extend(_bullet_lines(context_items))

        lines.extend(["", "## What To Read Next", ""])
        next_reads = payload.get("next_reads") or []
        if next_reads:
            for item in next_reads:
                if isinstance(item, dict):
                    label = str(item.get("label") or "Learner news next read").strip()
                    target = str(item.get("target") or "").strip()
                    reason = str(item.get("reason") or "").strip()
                    detail = " - ".join(part for part in [target, reason] if part)
                    lines.append(f"- **{label}**: {detail}" if detail else f"- **{label}**")
                elif item:
                    lines.append(f"- {item}")
        else:
            lines.append("- None")

        return "\n".join(lines).rstrip() + "\n"
    main_heading = "오늘 꼭 이해할 변화" if digest_type == "business" else "오늘 꼭 이해할 연구"
    lines = [
        "## 오늘의 한 줄",
        "",
        str(payload.get("one_line") or ""),
        "",
        "## 먼저 알면 좋은 배경",
        "",
    ]
    lines.extend(_bullet_lines(payload.get("background")))
    lines.extend(["", f"## {main_heading}", ""])

    main_items = payload.get("main_items") or []
    for index, item in enumerate(main_items, start=1):
        if not isinstance(item, dict):
            continue
        lines.extend([f"### {index}. {item.get('title', '').strip()}", ""])
        if item.get("what_happened"):
            lines.extend(["**무슨 일이 있었나**", "", str(item["what_happened"]), ""])
        if item.get("research_problem"):
            lines.extend(["**왜 이 문제가 있었나**", "", str(item["research_problem"]), ""])
        if item.get("what_changed"):
            what_changed_label = (
                "무엇이 쉬워졌나 / 무엇을 더 조심해야 하나"
                if digest_type == "research"
                else "이번 방법은 무엇을 덜 필요하게 하나"
            )
            lines.extend([f"**{what_changed_label}**", "", str(item["what_changed"]), ""])
        if item.get("why_people_care"):
            lines.extend(["**왜 사람들이 신경 쓰나**", "", str(item["why_people_care"]), ""])
        if item.get("business_relevance"):
            lines.extend(["**내 일과 무슨 관련이 있나**", "", str(item["business_relevance"]), ""])
        if item.get("dont_confuse"):
            lines.extend(["**헷갈리지 말 것**", "", str(item["dont_confuse"]), ""])
        if item.get("next_read"):
            lines.extend(["**다음에 읽을 학습자 뉴스**", "", str(item["next_read"]), ""])

    lines.extend(["## 오늘은 가볍게 지나가도 되는 소식", ""])
    skim_items = payload.get("skim_items") or []
    if skim_items:
        for item in skim_items:
            if isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                why_skim = str(item.get("why_skim") or "").strip()
                if title and why_skim:
                    lines.append(f"- **{title}**: {why_skim}")
                elif title:
                    lines.append(f"- {title}")
            elif item:
                lines.append(f"- {item}")
    else:
        lines.append("- 없음")

    context_items = payload.get("context") or []
    if context_items:
        lines.extend(["", "## 오늘의 맥락", ""])
        lines.extend(_bullet_lines(context_items))

    lines.extend(["", "## 더 읽어볼 만한 다음 뉴스", ""])
    next_reads = payload.get("next_reads") or []
    if next_reads:
        for item in next_reads:
            if isinstance(item, dict):
                label = str(item.get("label") or "학습자 뉴스 이어읽기").strip()
                target = str(item.get("target") or "").strip()
                reason = str(item.get("reason") or "").strip()
                detail = " - ".join(part for part in [target, reason] if part)
                lines.append(f"- **{label}**: {detail}" if detail else f"- **{label}**")
            elif item:
                lines.append(f"- {item}")
    else:
        lines.append("- 없음")

    return "\n".join(lines).rstrip() + "\n"


def render_markdown(
    payload: dict[str, Any],
    digest_type: str,
    batch_date: date,
    *,
    locale: str = "ko",
) -> str:
    type_title = digest_type.title()
    normalized_locale = _normalize_locale(locale)
    locale_label = f" ({normalized_locale})" if normalized_locale == "en" else ""
    lines = [
        f"# {batch_date.isoformat()} {type_title} Beginner Preview{locale_label}",
        "",
        "> Prototype only. Source: existing news_posts rows. No DB write.",
        "",
        render_article_markdown(payload, digest_type, locale=normalized_locale).rstrip(),
    ]
    return "\n".join(lines).rstrip() + "\n"


def load_beginner_artifact(path: Path) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    digest_type = str(artifact.get("digest_type") or "")
    locale = _normalize_locale(artifact.get("locale") or "ko")
    payload = artifact.get("payload")
    if digest_type not in {"research", "business"}:
        raise ValueError(f"Unsupported digest_type in artifact {path}: {digest_type!r}")
    if not isinstance(payload, dict):
        raise ValueError(f"Missing payload object in artifact {path}")
    validate_beginner_payload(payload, digest_type, locale=locale)
    return artifact


def _target_slug_for_locale(
    source_slugs: list[Any],
    batch_date: date,
    digest_type: str,
    locale: str,
) -> str:
    normalized_locale = _normalize_locale(locale)
    if normalized_locale == "en":
        return next(
            (
                str(slug)
                for slug in source_slugs
                if not str(slug).endswith("-ko")
            ),
            f"{batch_date.isoformat()}-{digest_type}-digest",
        )
    return next(
        (str(slug) for slug in source_slugs if str(slug).endswith("-ko")),
        f"{batch_date.isoformat()}-{digest_type}-digest-ko",
    )


def build_beginner_backfill_update(
    artifact: dict[str, Any],
    *,
    existing_guide_items: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    batch_date = _parse_date(str(artifact["date"]))
    digest_type = str(artifact["digest_type"])
    locale = _normalize_locale(artifact.get("locale") or "ko")
    payload = artifact["payload"]
    validate_beginner_payload(payload, digest_type, locale=locale)

    source_slugs = artifact.get("source_slugs") or slugs_for(batch_date, digest_type)
    target_slug = _target_slug_for_locale(source_slugs, batch_date, digest_type, locale)
    guide_items = dict(existing_guide_items or {})
    headline = str(payload.get("headline") or "").strip()
    one_line = str(payload.get("one_line") or "").strip()
    guide_items["title_beginner"] = headline
    guide_items["excerpt_beginner"] = one_line
    guide_items["beginner_backfill"] = {
        "source": "prototype_beginner_news",
        "date": batch_date.isoformat(),
        "digest_type": digest_type,
        "locale": locale,
    }

    return target_slug, {
        "content_beginner": render_article_markdown(payload, digest_type, locale=locale),
        "title_beginner": headline or None,
        "guide_items": guide_items,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def apply_beginner_backfill_file(
    supabase: Any,
    artifact_path: Path,
    *,
    dry_run: bool = False,
) -> tuple[str, dict[str, Any]]:
    artifact = load_beginner_artifact(artifact_path)
    batch_date = _parse_date(str(artifact["date"]))
    digest_type = str(artifact["digest_type"])
    locale = _normalize_locale(artifact.get("locale") or "ko")
    source_slugs = artifact.get("source_slugs") or slugs_for(batch_date, digest_type)
    target_slug = _target_slug_for_locale(source_slugs, batch_date, digest_type, locale)
    existing = (
        supabase.table("news_posts")
        .select("slug,guide_items")
        .eq("slug", target_slug)
        .single()
        .execute()
    )
    if not existing.data:
        raise RuntimeError(f"Missing target news_posts row for {target_slug}")

    slug, row = build_beginner_backfill_update(
        artifact,
        existing_guide_items=existing.data.get("guide_items") or {},
    )
    if not dry_run:
        supabase.table("news_posts").update(row).eq("slug", slug).execute()
    return slug, row


async def generate_beginner_preview(
    pair: DigestPair,
    *,
    locale: str = "ko",
    model: str | None = None,
    service_tier: str | None = "flex",
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required unless --prompt-only is used")

    model_name = model or settings.openai_model_light
    normalized_locale = _normalize_locale(locale)
    prompt = build_beginner_prompt(pair, locale=normalized_locale)
    editor_language = "English" if normalized_locale == "en" else "Korean"
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a careful {editor_language} news editor. Return JSON only. "
                "Do not add claims that are not grounded in the provided digest rows."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    client = get_openai_client()
    response = await client.chat.completions.create(
        **build_completion_kwargs(
            model=model_name,
            messages=messages,
            max_tokens=1_800,
            response_format={"type": "json_object"},
            reasoning_effort="low",
            service_tier=service_tier,
            verbosity="low",
            prompt_cache_key=f"beginner-news-prototype:{pair.digest_type}:{normalized_locale}",
        )
    )
    raw = response.choices[0].message.content or "{}"
    payload = parse_ai_json(raw, "beginner_news_prototype")
    usage = extract_usage_metrics(response, model_name, requested_service_tier=service_tier)
    try:
        validate_beginner_payload(payload, pair.digest_type, locale=normalized_locale)
    except ValueError as exc:
        revision_messages = messages + [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": build_revision_prompt(
                    payload,
                    str(exc),
                    locale=normalized_locale,
                ),
            },
        ]
        revision_response = await client.chat.completions.create(
            **build_completion_kwargs(
                model=model_name,
                messages=revision_messages,
                max_tokens=1_800,
                response_format={"type": "json_object"},
                reasoning_effort="low",
                service_tier=service_tier,
                verbosity="low",
                prompt_cache_key=f"beginner-news-prototype-revision:{pair.digest_type}:{normalized_locale}",
            )
        )
        revision_raw = revision_response.choices[0].message.content or "{}"
        payload = parse_ai_json(revision_raw, "beginner_news_prototype_revision")
        validate_beginner_payload(payload, pair.digest_type, locale=normalized_locale)
        usage = merge_usage_metrics(
            usage,
            extract_usage_metrics(
                revision_response,
                model_name,
                requested_service_tier=service_tier,
            ),
        )
    return payload, usage


def write_prompt_file(pair: DigestPair, output_dir: Path, *, locale: str = "ko") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_locale = _normalize_locale(locale)
    paths = output_paths(output_dir, pair.batch_date, pair.digest_type, locale=normalized_locale)
    paths["prompt"].write_text(
        build_beginner_prompt(pair, locale=normalized_locale),
        encoding="utf-8",
    )
    return paths["prompt"]


def write_preview_files(
    pair: DigestPair,
    payload: dict[str, Any],
    usage: dict[str, Any],
    output_dir: Path,
    *,
    locale: str = "ko",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_locale = _normalize_locale(locale)
    paths = output_paths(output_dir, pair.batch_date, pair.digest_type, locale=normalized_locale)
    artifact = {
        "date": pair.batch_date.isoformat(),
        "digest_type": pair.digest_type,
        "locale": normalized_locale,
        "source_slugs": slugs_for(pair.batch_date, pair.digest_type),
        "usage": usage,
        "payload": payload,
    }
    paths["json"].write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        render_markdown(
            payload,
            pair.digest_type,
            pair.batch_date,
            locale=normalized_locale,
        ),
        encoding="utf-8",
    )
    paths["prompt"].write_text(
        build_beginner_prompt(pair, locale=normalized_locale),
        encoding="utf-8",
    )
    return paths


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=_parse_date, required=True)
    parser.add_argument("--type", choices=["research", "business", "both"], default="both")
    parser.add_argument("--locale", choices=["ko", "en", "both"], default="ko")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Write prompt files only; skip OpenAI generation.",
    )
    parser.add_argument(
        "--standard-tier",
        action="store_true",
        help="Do not request OpenAI flex tier.",
    )
    parser.add_argument(
        "--apply-backfill",
        action="store_true",
        help="Write an existing local beginner JSON artifact into the selected locale news_posts row.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="For --apply-backfill, validate and print the target row without writing to Supabase.",
    )
    args = parser.parse_args()

    digest_types = ["research", "business"] if args.type == "both" else [args.type]
    locales = ["ko", "en"] if args.locale == "both" else [args.locale]
    supabase = get_supabase()
    service_tier = None if args.standard_tier else "flex"

    for digest_type in digest_types:
        pair = fetch_digest_pair(supabase, args.date, digest_type)
        for locale in locales:
            if args.apply_backfill:
                artifact_path = output_paths(
                    args.output_dir,
                    args.date,
                    digest_type,
                    locale=locale,
                )["json"]
                slug, row = apply_beginner_backfill_file(
                    supabase,
                    artifact_path,
                    dry_run=args.dry_run,
                )
                mode = "would update" if args.dry_run else "updated"
                print(
                    f"{digest_type}/{locale}: {mode} {slug} "
                    f"(title_beginner={row.get('title_beginner')!r}, chars={len(row.get('content_beginner') or '')})"
                )
                continue

            prompt_path = write_prompt_file(pair, args.output_dir, locale=locale)
            print(f"{digest_type}/{locale}: wrote prompt {prompt_path}")

            if args.prompt_only:
                continue

            payload, usage = await generate_beginner_preview(
                pair,
                locale=locale,
                model=args.model,
                service_tier=service_tier,
            )
            paths = write_preview_files(
                pair,
                payload,
                usage,
                args.output_dir,
                locale=locale,
            )
            cost = usage.get("cost_usd")
            cost_text = f"${cost:.4f}" if isinstance(cost, (int, float)) else "unknown cost"
            print(
                f"{digest_type}/{locale}: wrote {paths['markdown']} and {paths['json']} "
                f"(tokens={usage.get('tokens_used')}, cost={cost_text})"
            )


if __name__ == "__main__":
    asyncio.run(main())
