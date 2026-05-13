from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.prototype_beginner_news import (
    DigestPair,
    READER_FACING_BLOCKING_STACK_TERMS,
    build_beginner_backfill_update,
    build_beginner_prompt,
    build_revision_prompt,
    output_paths,
    render_article_markdown,
    render_markdown,
    validate_beginner_payload,
)


def _row(slug: str, locale: str) -> dict:
    return {
        "slug": slug,
        "locale": locale,
        "title": "Agent benchmarks moved from demos to deployment decisions",
        "excerpt": "New agent benchmarks are being used as buying signals by enterprise teams.",
        "source_urls": [
            "https://example.com/agent-benchmark",
            "https://example.com/enterprise-ai",
        ],
        "content_expert": "Expert digest body covering several market and technical stories.",
        "content_learner": "Learner digest body with practical context and a few technical terms.",
        "guide_items": [
            {
                "title": "Agent benchmark adoption",
                "persona": "learner",
                "score": 92,
            }
        ],
        "frontload": [
            {
                "title": "Benchmarks are becoming buying signals",
                "persona": "learner",
                "score": 91,
            }
        ],
    }


def _pair(digest_type: str) -> DigestPair:
    batch_date = date(2026, 5, 11)
    base_slug = f"{batch_date.isoformat()}-{digest_type}-digest"
    return DigestPair(
        batch_date=batch_date,
        digest_type=digest_type,
        en=_row(base_slug, "en"),
        ko=_row(f"{base_slug}-ko", "ko"),
    )


def _valid_business_item(title: str = "현장 지원 방식이 기업 도입 기준이 된다") -> dict:
    return {
        "title": title,
        "what_happened": "공급사가 고객사 가까이에서 문제를 함께 푸는 방식이 강조됐다.",
        "why_people_care": "실제 업무에 붙이는 과정에서 빠른 수정과 책임 소재가 중요하기 때문이다.",
        "business_relevance": "도입 담당자는 기능 비교뿐 아니라 운영 지원 방식도 확인해야 한다.",
        "dont_confuse": "모든 고객에게 같은 지원 조직이 붙는다는 뜻은 아니다.",
        "next_read": "학습자 뉴스의 기업 도입 섹션",
    }


def _valid_research_item(title: str = "실행 없이 좋은 후보를 먼저 좁힌다") -> dict:
    return {
        "title": title,
        "what_happened": "모델을 직접 돌리기 전에 성능 가능성이 높은 후보를 추리는 방법이 나왔다.",
        "why_people_care": "비싼 실험을 모두 하지 않아도 다음에 볼 대상을 줄일 수 있기 때문이다.",
        "research_problem": "모델 후보가 많아질수록 전부 실행해 비교하기 어렵다.",
        "what_changed": "비싼 실행 없이 후보를 먼저 줄일 수 있다.",
        "dont_confuse": "최종 성능을 보장하는 자동 선택기는 아니다.",
        "next_read": "학습자 뉴스의 모델 선택 섹션",
    }


def test_business_beginner_prompt_limits_scope_and_uses_work_context() -> None:
    prompt = build_beginner_prompt(_pair("business"))

    assert "메인 2-3개" in prompt
    assert "모든 소식을 깊게 다루지 마세요" in prompt
    assert "가볍게 지나가도 되는 소식" in prompt
    assert "내 일과 무슨 관련이 있나" in prompt
    assert "헷갈리지 말 것" in prompt
    assert "학습자 뉴스 이어읽기 경로" in prompt
    assert "용어 정의를 길게 반복하지 마세요" in prompt
    assert "내부 필드명" in prompt
    assert "프로젝트명보다 변화의 의미를 먼저" in prompt
    assert "headline, one_line, and main item titles" in prompt
    assert "Bad: \"Hermes Agent v0.13" in prompt
    assert "Good: \"반복 업무를 이어서 처리하는 에이전트 업데이트" in prompt
    assert "임베디드 배치" in prompt
    assert "현장 임베딩" in prompt
    assert "배치 법인" in prompt
    assert "고객사 상주" in prompt
    assert "Surface-change-first rule" in prompt
    assert "reader-facing fields" in prompt
    assert "Do not put infrastructure stack names" in prompt
    assert "https://example.com/agent-benchmark" in prompt


def test_beginner_prompt_adds_main_only_term_density_and_skim_rules() -> None:
    prompt = build_beginner_prompt(_pair("research"))

    assert "one_line may summarize only selected main_items" in prompt
    assert "Do not mention skim_items or non-main stories in one_line" in prompt
    assert "Research main item body may use at most 2 technical method terms" in prompt
    assert "what_changed must answer which burden is reduced" in prompt
    assert "Each skim_items.why_skim must be 35 Korean words or fewer" in prompt


def test_business_beginner_prompt_makes_one_line_a_lens_not_catalog() -> None:
    prompt = build_beginner_prompt(_pair("business"))

    assert "Business one_line is a lens sentence, not a catalog" in prompt
    assert "Do not list vendor, product, equipment, or project names in business one_line" in prompt
    assert "put concrete names and examples in main_items instead" in prompt
    assert "Do not write reading instructions like 보세요" in prompt


def test_research_beginner_prompt_uses_research_context_not_business_context() -> None:
    prompt = build_beginner_prompt(_pair("research"))

    assert "Research Beginner main_items: 1-2" in prompt
    assert "한마디로 무슨 변화인가" in prompt
    assert "이번 방법은 무엇을 덜 필요하게 하나" in prompt
    assert "내 일과 무슨 관련이 있나" not in prompt


def test_research_beginner_prompt_limits_main_items_to_one_or_two() -> None:
    prompt = build_beginner_prompt(_pair("research"))

    assert "Research Beginner main_items: 1-2" in prompt
    assert "Do not use 3 main_items for research" in prompt
    assert "한마디로 무슨 변화인가" in prompt
    assert "이번 방법은 무엇을 덜 필요하게 하나" in prompt


def test_validate_research_payload_accepts_one_item_and_rejects_three() -> None:
    item = {
        "title": "작은 모델을 더 싸게 가르치려는 방법",
        "what_happened": "교사 모델의 내부값 없이도 학생 모델을 평가하는 방법이 나왔다.",
        "why_people_care": "상용 모델을 직접 들여다볼 수 없어도 작은 모델을 맞출 수 있기 때문이다.",
        "research_problem": "기존 방식은 교사 모델의 내부 확률값이 필요했다.",
        "what_changed": "내부값 대신 비교에서 만든 채점 기준을 쓴다.",
        "dont_confuse": "항상 모든 도메인에서 강하다는 뜻은 아니다.",
        "next_read": "학습자 뉴스의 ROPD 섹션",
    }
    valid_payload = {
        "headline": "작은 모델 학습 비용을 줄이려는 연구",
        "one_line": "큰 모델의 내부를 몰라도 작은 모델을 비슷하게 가르치려는 방법이 나왔다.",
        "background": ["상용 모델은 내부값을 공개하지 않는 경우가 많다."],
        "main_items": [item],
        "skim_items": [],
        "next_reads": [],
    }
    validate_beginner_payload(valid_payload, "research")

    invalid_payload = {**valid_payload, "main_items": [item, item, item]}
    with pytest.raises(ValueError, match="research main_items"):
        validate_beginner_payload(invalid_payload, "research")


def test_validate_research_payload_rejects_blocking_jargon_in_one_line() -> None:
    item = {
        "title": "작은 모델을 더 싸게 가르치려는 방법",
        "what_happened": "교사 모델의 내부값 없이도 학생 모델을 평가하는 방법이 나왔다.",
        "why_people_care": "상용 모델을 직접 들여다볼 수 없어도 작은 모델을 맞출 수 있기 때문이다.",
        "research_problem": "기존 방식은 교사 모델의 내부 확률값이 필요했다.",
        "what_changed": "내부값 대신 비교에서 만든 채점 기준을 쓴다.",
        "dont_confuse": "항상 모든 도메인에서 강하다는 뜻은 아니다.",
        "next_read": "학습자 뉴스의 ROPD 섹션",
    }
    payload = {
        "headline": "작은 모델 학습 비용을 줄이려는 연구",
        "one_line": "루브릭 증류와 MoE 전문가 풀 공유가 비용 절감 경로를 제시한다.",
        "background": ["상용 모델은 내부값을 공개하지 않는 경우가 많다."],
        "main_items": [item],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="research one_line"):
        validate_beginner_payload(payload, "research")


def test_validate_one_line_rejects_skim_only_story_markers() -> None:
    payload = {
        "headline": "기업 AI 도입 기준이 운영 지원으로 이동한다",
        "one_line": "Hermes 업데이트와 기업 도입 지원 방식이 함께 주목받고 있다.",
        "background": ["입문자는 오늘 꼭 볼 변화와 가볍게 볼 소식을 구분해야 한다."],
        "main_items": [
            _valid_business_item("기업 도입은 현장 지원 방식까지 비교하게 된다"),
            _valid_business_item("보안 검증 요구가 조달 과정의 부담이 된다"),
        ],
        "skim_items": [
            {
                "title": "Hermes Agent v0.13 update",
                "why_skim": "방향은 참고할 만하지만 오늘의 핵심 변화는 아니다.",
            }
        ],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="one_line must summarize only selected main_items"):
        validate_beginner_payload(payload, "business")


def test_validate_business_one_line_rejects_catalog_like_name_lists() -> None:
    payload = {
        "headline": "AI 인프라 경쟁은 용량 확보와 운영 효율로 이동한다",
        "one_line": (
            "공급과 용량을 금융으로 묶어 우선 접근권을 확보하려는 움직임"
            "(엔비디아 400억 달러 지분투자)과, 장비 운영 방식"
            "(GB200, NVL72, Slurm, NCCL Inspector)이 동시에 바뀌고 있다."
        ),
        "background": ["비즈니스 입문자는 구체 제품명보다 변화의 관점을 먼저 잡아야 한다."],
        "main_items": [
            _valid_business_item("용량 확보 경쟁이 구매 전략을 바꾼다"),
            _valid_business_item("비싼 장비를 나눠 쓰는 운영 방식이 중요해진다"),
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="business one_line must be a lens sentence"):
        validate_beginner_payload(payload, "business")


def test_validate_business_one_line_allows_lens_sentence_without_name_list() -> None:
    payload = {
        "headline": "AI 인프라 경쟁은 용량 확보와 운영 효율로 이동한다",
        "one_line": "AI 인프라 경쟁은 칩 성능만이 아니라 먼저 쓸 수 있는 용량과 비싼 장비를 나눠 쓰는 운영 능력을 함께 보는 문제로 옮겨가고 있다.",
        "background": ["구체 사례는 본문에서 풀고, 한 줄 요약은 오늘 볼 관점을 잡아준다."],
        "main_items": [
            _valid_business_item("용량 확보 경쟁이 구매 전략을 바꾼다"),
            _valid_business_item("비싼 장비를 나눠 쓰는 운영 방식이 중요해진다"),
        ],
        "skim_items": [],
        "next_reads": [],
    }

    validate_beginner_payload(payload, "business")


def test_validate_one_line_rejects_reader_instruction_phrasing() -> None:
    payload = {
        "headline": "AI 인프라 경쟁은 용량 확보와 운영 효율로 이동한다",
        "one_line": "공급능력과 운영 효율이라는 관점으로 오늘 소식을 보세요.",
        "background": ["관점문은 기사 문장처럼 보여야 한다."],
        "main_items": [
            _valid_business_item("용량 확보 경쟁이 구매 전략을 바꾼다"),
            _valid_business_item("비싼 장비를 나눠 쓰는 운영 방식이 중요해진다"),
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="one_line must state the lens"):
        validate_beginner_payload(payload, "business")


def test_validate_research_payload_rejects_dense_method_terms_before_dont_confuse() -> None:
    item = {
        **_valid_research_item("라우팅 기준으로 후보를 좁힌다"),
        "what_happened": "로짓, 퍼플렉시티, 검증 손실을 함께 비교해 후보를 고른다.",
        "what_changed": "비싼 실행 없이 비교 후보를 줄일 수 있다.",
    }
    payload = {
        "headline": "비싼 실험 전에 후보를 줄이려는 연구",
        "one_line": "모든 후보를 돌리기 전에 먼저 볼 대상을 줄이는 방법이 나왔다.",
        "background": ["입문자는 방법 이름보다 왜 실험 부담이 줄어드는지 먼저 보면 된다."],
        "main_items": [item],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="technical term density"):
        validate_beginner_payload(payload, "research")


def test_validate_research_payload_allows_related_method_family_terms() -> None:
    item = {
        **_valid_research_item("배포 메모리를 줄이는 모델 실행 방식"),
        "what_happened": "MoE 모델에서 라우팅과 전문가 풀 공유를 함께 써서 필요한 부분만 켠다.",
        "what_changed": "모델 실행 때 필요한 메모리와 비용을 줄일 수 있다.",
    }
    payload = {
        "headline": "모델 실행에 필요한 메모리를 줄이는 연구",
        "one_line": "큰 모델을 돌릴 때 필요한 부분만 쓰려는 방법이 나왔다.",
        "background": ["같은 기술 묶음의 용어는 짧게 함께 설명할 수 있다."],
        "main_items": [item],
        "skim_items": [],
        "next_reads": [],
    }

    validate_beginner_payload(payload, "research")


def test_validate_research_what_changed_requires_burden_reduction() -> None:
    item = {
        **_valid_research_item(),
        "what_changed": "새로운 비교 방법을 제안했다.",
    }
    payload = {
        "headline": "모델 후보를 고르는 연구",
        "one_line": "모델 후보를 비교하는 새 접근이 나왔다.",
        "background": ["입문자는 연구가 어떤 부담을 줄이는지 먼저 봐야 한다."],
        "main_items": [item],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="what_changed must explain which burden is reduced"):
        validate_beginner_payload(payload, "research")


def test_validate_skim_items_reject_long_why_skim() -> None:
    payload = {
        "headline": "기업 AI 도입 기준이 운영 지원으로 이동한다",
        "one_line": "기업 도입은 기능보다 운영 지원과 보안 검증을 함께 보게 됐다.",
        "background": ["가볍게 볼 소식은 짧게 남겨야 한다."],
        "main_items": [
            _valid_business_item("기업 도입은 현장 지원 방식까지 비교하게 된다"),
            _valid_business_item("보안 검증 요구가 조달 과정의 부담이 된다"),
        ],
        "skim_items": [
            {
                "title": "작은 도구 업데이트",
                "why_skim": " ".join(f"단어{i}" for i in range(36)),
            }
        ],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="skim_items"):
        validate_beginner_payload(payload, "business")


def test_validate_business_payload_still_requires_two_to_three_items() -> None:
    item = {
        "title": "기업 도입 방식이 현장 지원 중심으로 이동",
        "what_happened": "벤더가 고객사에 엔지니어를 보내는 방식이 보도됐다.",
        "why_people_care": "복잡한 업무 연동에는 현장 검증이 필요하기 때문이다.",
        "business_relevance": "파일럿 설계와 성과 지표를 미리 정해야 한다.",
        "dont_confuse": "모든 고객에게 같은 방식이 적용된다는 뜻은 아니다.",
        "next_read": "학습자 뉴스의 기업 도입 섹션",
    }
    payload = {
        "headline": "기업 AI 도입 방식 변화",
        "one_line": "기업 AI 도입이 현장 지원 중심으로 이동하고 있다.",
        "background": ["기업은 AI를 업무에 붙이는 데 더 많은 지원을 요구한다."],
        "main_items": [item],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="business main_items"):
        validate_beginner_payload(payload, "business")


def test_validate_reader_facing_fields_reject_stack_or_abstract_terms() -> None:
    item = {
        "title": "GB200 NVL72 + Slurm로 작업 스케줄링 방식이 바뀜",
        "what_happened": "대형 GPU 랙에서 작업을 더 잘 나눠 쓰려는 운영 방식이 나왔다.",
        "why_people_care": "비싼 장비를 놀리지 않고 쓰는 일이 중요하기 때문이다.",
        "business_relevance": "인프라 담당자는 장비 구매보다 운영 병목을 먼저 점검해야 한다.",
        "dont_confuse": "특정 장비를 사면 자동으로 효율이 오른다는 뜻은 아니다.",
        "next_read": "학습자 뉴스의 GPU 운영 섹션",
    }
    payload = {
        "headline": "인프라 운영 비용을 줄이려는 변화",
        "one_line": "비싼 AI 서버를 더 효율적으로 나눠 쓰려는 운영 변화가 나오고 있다.",
        "background": ["AI 인프라는 장비 구매보다 운영 효율이 더 중요해지고 있다."],
        "main_items": [
            item,
            {
                **item,
                "title": "장비 운영 지표를 더 빨리 보는 방식이 중요해짐",
                "next_read": "학습자 뉴스의 관측성 섹션",
            },
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="surface-change"):
        validate_beginner_payload(payload, "business")


def test_stack_replacement_values_are_korean_beginner_phrases() -> None:
    assert READER_FACING_BLOCKING_STACK_TERMS["ROCm"] == "GPU에서 모델을 돌리기 위한 소프트웨어 환경"
    assert READER_FACING_BLOCKING_STACK_TERMS["vLLM"] == "모델을 빠르게 실행하기 위한 도구"
    assert READER_FACING_BLOCKING_STACK_TERMS["온디바이스"] == "클라우드에 보내지 않고 기기에서 처리하는 방식"
    assert not any("software stack" in value for value in READER_FACING_BLOCKING_STACK_TERMS.values())
    assert not any("model serving engine" in value for value in READER_FACING_BLOCKING_STACK_TERMS.values())


def test_validate_reader_fields_rejects_revision_replacement_leakage() -> None:
    item = {
        "title": "클라우드 비용과 지연을 줄이는 실행 경로가 늘어남",
        "what_happened": "일부 장비에서 모델을 로컬로 더 빠르게 돌릴 수 있는 선택지가 늘었다.",
        "why_people_care": "민감한 데이터나 응답 속도가 중요한 업무에서 클라우드 의존을 줄일 수 있다.",
        "business_relevance": "팀은 장비 호환성과 운영 비용을 함께 비교해야 한다.",
        "dont_confuse": "모든 장비에서 바로 안정적으로 운영된다는 뜻은 아니다.",
        "next_read": "학습자 뉴스의 로컬 실행 섹션",
    }
    payload = {
        "headline": "로컬 실행 선택지가 늘어남",
        "one_line": "예: model serving engine GPU software stack 통합으로 로컬 실행 선택지가 늘었다.",
        "background": ["로컬 실행은 비용과 지연을 줄일 수 있지만 환경 제약이 있다."],
        "main_items": [
            item,
            {
                **item,
                "title": "장비 호환성 점검이 더 중요해짐",
                "next_read": "학습자 뉴스의 장비 호환성 섹션",
            },
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="surface-change"):
        validate_beginner_payload(payload, "business")


def test_validate_reader_field_surface_errors_are_aggregated() -> None:
    item = {
        "title": "온디바이스 추론 옵션이 늘어남",
        "what_happened": "일부 장비에서 모델을 로컬로 더 빠르게 돌릴 수 있는 선택지가 늘었다.",
        "why_people_care": "민감한 데이터나 응답 속도가 중요한 업무에서 클라우드 의존을 줄일 수 있다.",
        "business_relevance": "팀은 장비 호환성과 운영 비용을 함께 비교해야 한다.",
        "dont_confuse": "모든 장비에서 바로 안정적으로 운영된다는 뜻은 아니다.",
        "next_read": "학습자 뉴스의 로컬 실행 섹션",
    }
    payload = {
        "headline": "로컬 실행 선택지가 늘어남",
        "one_line": "vLLM ROCm 통합으로 로컬 실행 선택지가 늘었다.",
        "background": ["로컬 실행은 비용과 지연을 줄일 수 있지만 환경 제약이 있다."],
        "main_items": [
            item,
            {
                **item,
                "title": "장비 호환성 점검이 더 중요해짐",
                "next_read": "학습자 뉴스의 장비 호환성 섹션",
            },
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError) as exc:
        validate_beginner_payload(payload, "business")
    message = str(exc.value)
    assert "surface-change" in message
    assert "one_line" in message
    assert "main_items[1].title" in message


def test_validate_beginner_payload_rejects_too_many_main_items() -> None:
    payload = {
        "headline": "오늘의 AI 흐름",
        "one_line": "벤치마크가 구매 판단으로 이동하고 있다.",
        "background": ["기업은 AI 도입 기준을 더 구체화하고 있다."],
        "main_items": [
            {"title": "Item 1"},
            {"title": "Item 2"},
            {"title": "Item 3"},
            {"title": "Item 4"},
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="main_items"):
        validate_beginner_payload(payload, "business")


def test_validate_beginner_payload_rejects_internal_field_names() -> None:
    payload = {
        "headline": "오늘의 AI 흐름",
        "one_line": "AI 도구 선택 기준이 검증 결과로 이동하고 있다.",
        "background": ["기업은 AI 도입 기준을 더 구체화하고 있다."],
        "main_items": [
            {
                "title": "벤치마크가 구매 신호가 되다",
                "what_happened": "새 벤치마크가 엔터프라이즈 평가에 쓰였다.",
                "why_people_care": "도입 담당자는 숫자로 비교할 근거가 필요하다.",
                "business_relevance": "AI 도구 선택 기준이 데모에서 검증 결과로 이동한다.",
                "dont_confuse": "벤치마크 1위가 항상 현장 성능 1위라는 뜻은 아니다.",
                "next_read": "content_learner 섹션을 이어서 읽기",
            },
            {
                "title": "에이전트 기능이 운영 기능으로 이동하다",
                "what_happened": "상태 관리와 복구 기능이 강조됐다.",
                "why_people_care": "실제 업무에서는 중단 후 재개가 중요하다.",
                "business_relevance": "반복 업무 자동화의 실패 비용을 줄일 수 있다.",
                "dont_confuse": "기능 추가가 곧바로 전사 도입 근거라는 뜻은 아니다.",
                "next_read": "학습자 뉴스의 에이전트 운영 섹션",
            },
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="internal field"):
        validate_beginner_payload(payload, "business")


def test_validate_beginner_payload_rejects_schema_label_placeholders() -> None:
    payload = {
        "headline": "점검 비용과 실패 패턴이 더 잘 보이기 시작했다",
        "one_line": "실행과 검증에서 실제 부담을 줄이거나 설명하는 연구가 나왔다.",
        "background": ["입문자는 라벨이 아니라 실제 설명을 읽어야 한다."],
        "main_items": [
            {
                **_valid_research_item("실패 위험을 먼저 드러내는 평가 방식"),
                "research_problem": "왜 이 문제가 있었나",
                "what_changed": "이번 방법은 무엇을 덜 필요하게 하나",
                "dont_confuse": "헷갈리지 말 것",
            }
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="schema placeholder"):
        validate_beginner_payload(payload, "research")


def test_validate_beginner_payload_rejects_project_or_method_first_framing() -> None:
    payload = {
        "headline": "오늘의 AI 연구 흐름",
        "one_line": "ActCam은 추가 학습 없이 카메라와 동작을 제어한다.",
        "background": ["영상 AI는 제어 비용을 줄이는 방향으로 움직이고 있다."],
        "main_items": [
            {
                "title": "MoE 전문 파라미터를 전역 풀에서 공유",
                "what_happened": "큰 모델을 더 가볍게 쓰기 위한 설계가 나왔다.",
                "why_people_care": "모델 운영 비용을 낮출 수 있기 때문이다.",
                "research_problem": "모델이 커질수록 필요한 부품도 함께 늘어난다.",
                "what_changed": "부품을 층마다 따로 두지 않고 공유하는 방식을 제안했다.",
                "dont_confuse": "바로 모든 대형 모델에 적용된다는 뜻은 아니다.",
                "next_read": "학습자 뉴스의 모델 효율화 섹션",
            },
            {
                "title": "영상 제어를 더 적은 추가 학습으로 처리",
                "what_happened": "영상 생성 중 카메라와 동작 제어를 함께 다루는 연구가 나왔다.",
                "why_people_care": "영상 제작 도구의 반복 작업을 줄일 수 있기 때문이다.",
                "research_problem": "기존 방식은 원하는 움직임을 맞추려면 추가 조정이 많이 필요했다.",
                "what_changed": "입력 조건을 단계별로 조합해 제어한다.",
                "dont_confuse": "상용 영상 제작 도구에 바로 들어갔다는 뜻은 아니다.",
                "next_read": "학습자 뉴스의 영상 제어 섹션",
            },
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="meaning-first"):
        validate_beginner_payload(payload, "research")


def test_validate_beginner_payload_rejects_embedded_deployment_literalism() -> None:
    payload = {
        "headline": "기업 AI 도입 방식 변화",
        "one_line": "대기업 도입은 외부 데모에서 엔지니어를 고객사에 두는 임베디드 배치로 이동하고 있다.",
        "background": ["기업은 AI 도입 과정에서 더 밀착된 지원을 요구한다."],
        "main_items": [
            {
                "title": "기업 고객 옆에서 도입을 돕는 방식이 늘어남",
                "what_happened": "전담 엔지니어가 고객사와 함께 문제를 푸는 방식이 보도됐다.",
                "why_people_care": "구매 전환에 필요한 현장 검증이 중요해졌기 때문이다.",
                "business_relevance": "도구 도입은 기능 비교보다 운영 지원 역량을 더 보게 된다.",
                "dont_confuse": "모든 고객사에 같은 방식으로 배정된다는 뜻은 아니다.",
                "next_read": "학습자 뉴스의 엔터프라이즈 도입 섹션",
            },
            {
                "title": "보안 검증 요구도 함께 커짐",
                "what_happened": "AI 도구 도입 전 보안 검토가 더 중요해졌다.",
                "why_people_care": "취약점 발견 속도와 조달 기준이 함께 바뀌고 있기 때문이다.",
                "business_relevance": "계약 전 보안·법무 검토 시간이 늘 수 있다.",
                "dont_confuse": "즉시 모든 조달이 중단된다는 뜻은 아니다.",
                "next_read": "학습자 뉴스의 보안 검증 섹션",
            },
        ],
        "skim_items": [],
        "next_reads": [],
    }

    with pytest.raises(ValueError, match="literal translation"):
        validate_beginner_payload(payload, "business")


def test_build_revision_prompt_asks_for_full_json_with_validation_error() -> None:
    invalid_payload = {
        "headline": "오늘의 AI 흐름",
        "one_line": "AI 도구의 운영 기능이 중요해지고 있다.",
        "main_items": [{"title": "Hermes Agent v0.13 운영 기능 강화"}],
    }

    prompt = build_revision_prompt(
        invalid_payload,
        "main_items[1].title must be meaning-first",
    )

    assert "main_items[1].title must be meaning-first" in prompt
    assert "Return the full corrected JSON" in prompt
    assert "do not start with project or method names" in prompt
    assert "Research outputs must use 1-2 main_items" in prompt
    assert "research one_line must not contain" in prompt
    assert "Surface-change-first" in prompt
    assert "infrastructure stack names" in prompt
    assert "re-check every validation rule before returning" in prompt
    assert "Business one_line should usually contain zero parentheses" in prompt
    assert '"온디바이스" -> "클라우드에 보내지 않고 기기에서 처리하는 방식"' in prompt
    assert '"작업 스케줄링" -> "비싼 장비를 나눠 쓰는 방식"' in prompt
    assert "apply it literally" in prompt
    assert "Hermes Agent v0.13 운영 기능 강화" in prompt


def test_render_markdown_writes_beginner_sections() -> None:
    payload = {
        "headline": "오늘의 AI 비즈니스 흐름",
        "one_line": "벤치마크가 이제 제품 선택의 기준으로 쓰이기 시작했다.",
        "background": ["기업은 성능 주장보다 실제 업무 적합성을 더 따지고 있다."],
        "main_items": [
            {
                "title": "벤치마크가 구매 신호가 되다",
                "what_happened": "새 벤치마크가 엔터프라이즈 평가에 쓰였다.",
                "why_people_care": "도입 담당자는 숫자로 비교할 근거가 필요하다.",
                "business_relevance": "AI 도구 선택 기준이 데모에서 검증 결과로 이동한다.",
                "dont_confuse": "벤치마크 1위가 항상 현장 성능 1위라는 뜻은 아니다.",
                "next_read": "학습자 뉴스의 벤치마크 해설을 이어서 읽으면 좋다.",
            }
        ],
        "skim_items": [
            {
                "title": "작은 모델 업데이트",
                "why_skim": "큰 방향은 바꾸지 않지만 도구 선택 때 참고할 만하다.",
            }
        ],
        "context": ["벤치마크는 점점 제품 포지셔닝 언어가 되고 있다."],
        "next_reads": [
            {
                "label": "학습자 뉴스 이어읽기",
                "target": "Agent benchmark adoption",
                "reason": "벤치마크가 왜 중요한지 더 자세히 볼 수 있다.",
            }
        ],
    }

    markdown = render_markdown(payload, "business", date(2026, 5, 11))

    assert markdown.startswith("# 2026-05-11 Business Beginner Preview")
    assert "## 오늘의 한 줄" in markdown
    assert "## 먼저 알면 좋은 배경" in markdown
    assert "## 오늘 꼭 이해할 변화" in markdown
    assert "### 1. 벤치마크가 구매 신호가 되다" in markdown
    assert "**내 일과 무슨 관련이 있나**" in markdown
    assert "## 오늘은 가볍게 지나가도 되는 소식" in markdown
    assert "## 더 읽어볼 만한 다음 뉴스" in markdown


def test_render_article_markdown_omits_prototype_header() -> None:
    payload = {
        "headline": "오늘의 AI 비즈니스 흐름",
        "one_line": "벤치마크가 이제 제품 선택의 기준으로 쓰이기 시작했다.",
        "background": ["기업은 성능 주장보다 실제 업무 적합성을 더 따지고 있다."],
        "main_items": [
            {
                "title": "벤치마크가 구매 신호가 되다",
                "what_happened": "새 벤치마크가 엔터프라이즈 평가에 쓰였다.",
                "why_people_care": "도입 담당자는 숫자로 비교할 근거가 필요하다.",
                "business_relevance": "AI 도구 선택 기준이 데모에서 검증 결과로 이동한다.",
                "dont_confuse": "벤치마크 1위가 항상 현장 성능 1위라는 뜻은 아니다.",
                "next_read": "학습자 뉴스의 벤치마크 해설을 이어서 읽으면 좋다.",
            }
        ],
        "skim_items": [],
        "next_reads": [],
    }

    markdown = render_article_markdown(payload, "business")

    assert markdown.startswith("## 오늘의 한 줄")
    assert "Prototype only" not in markdown
    assert "Beginner Preview" not in markdown


def test_build_beginner_backfill_update_merges_existing_guide_items() -> None:
    artifact = {
        "date": "2026-05-11",
        "digest_type": "business",
        "source_slugs": ["2026-05-11-business-digest", "2026-05-11-business-digest-ko"],
        "payload": {
            "headline": "기업 AI 도입 기준이 운영 지원으로 이동",
            "one_line": "기업 AI 도입은 기능보다 운영 지원과 보안 검증을 함께 보게 됐다.",
            "background": ["기업은 AI 도입 기준을 더 구체화하고 있다."],
            "main_items": [
                _valid_business_item("기업 도입은 현장 지원 방식까지 비교하게 된다"),
                _valid_business_item("보안 검증 요구가 조달 과정의 부담이 된다"),
            ],
            "skim_items": [],
            "next_reads": [],
        },
    }

    slug, row = build_beginner_backfill_update(
        artifact,
        existing_guide_items={"quiz_poll_learner": {"question": "keep me"}},
    )

    assert slug == "2026-05-11-business-digest-ko"
    assert row["content_beginner"].startswith("## 오늘의 한 줄")
    assert "Prototype only" not in row["content_beginner"]
    assert row["title_beginner"] == "기업 AI 도입 기준이 운영 지원으로 이동"
    assert row["guide_items"]["title_beginner"] == "기업 AI 도입 기준이 운영 지원으로 이동"
    assert row["guide_items"]["excerpt_beginner"] == "기업 AI 도입은 기능보다 운영 지원과 보안 검증을 함께 보게 됐다."
    assert row["guide_items"]["quiz_poll_learner"] == {"question": "keep me"}


def test_render_markdown_uses_beginner_research_section_labels() -> None:
    payload = {
        "headline": "오늘의 AI 연구 흐름",
        "one_line": "큰 모델의 내부를 몰라도 작은 모델을 가르치려는 방법이 나왔다.",
        "background": ["상용 모델은 내부값을 공개하지 않는 경우가 많다."],
        "main_items": [
            {
                "title": "작은 모델을 더 싸게 가르치려는 방법",
                "what_happened": "교사 모델의 내부값 없이도 학생 모델을 평가하는 방법이 나왔다.",
                "why_people_care": "작은 모델을 더 적은 접근권한으로 맞출 수 있기 때문이다.",
                "research_problem": "기존 방식은 교사 모델의 내부 확률값이 필요했다.",
                "what_changed": "내부값 대신 비교에서 만든 채점 기준을 쓴다.",
                "dont_confuse": "항상 모든 도메인에서 강하다는 뜻은 아니다.",
                "next_read": "학습자 뉴스의 ROPD 섹션",
            }
        ],
        "skim_items": [],
        "next_reads": [],
    }

    markdown = render_markdown(payload, "research", date(2026, 5, 12))

    assert "**왜 이 문제가 있었나**" in markdown
    assert "**이번 방법은 무엇을 덜 필요하게 하나**" in markdown
    assert "**기존 방식은 뭐가 어려웠나**" not in markdown
    assert "**이번엔 뭐가 달라졌나**" not in markdown


def test_output_paths_are_date_and_type_scoped(tmp_path: Path) -> None:
    paths = output_paths(tmp_path, date(2026, 5, 11), "research")

    assert paths["json"] == tmp_path / "2026-05-11-research-beginner.json"
    assert paths["markdown"] == tmp_path / "2026-05-11-research-beginner.md"
    assert paths["prompt"] == tmp_path / "2026-05-11-research-beginner.prompt.txt"
