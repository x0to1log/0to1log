---
title: Handbook Content Rules
tags:
  - content
  - handbook
  - rules
source: docs/08_Handbook.md
---

# Handbook Content Rules

Handbook(AI Glossary) 콘텐츠 작성 규칙. 용어집은 참조형 페이지이므로, 뉴스/블로그와는 다른 톤과 구조를 따른다.

## 콘텐츠 철학

> [!important] 핵심 원칙
> Glossary는 ==댓글 페이지가 아니라 참조형 페이지==다. 빠른 이해가 핵심이며, 토론보다 설명 개선 신호 수집에 집중한다.

- 뉴스 상세: 해석과 의견 교환 → 댓글이 자연스러움
- Handbook: 참조형 → lightweight feedback (`도움 됨` / `헷갈림`)이 더 적합

## 레벨 체계

Handbook는 뉴스의 3페르소나(입문자/학습자/현직자)와 달리 ==2단계==만 사용한다.

| Level | 목적 | 톤 | 대상 |
|---|---|---|---|
| **basic** | 빠른 이해, 쉬운 설명 | 읽는 중 바로 참고할 수 있는 간결한 설명 | 입문자, 빠른 참조 |
| **advanced** | 더 기술적인 설명 | 실무/구조 관점의 깊은 설명 | 학습자, 현직자 |

- 사용자의 `profiles.handbook_level` (default: `basic`)이 기본 노출 레벨
- 비로그인 사용자는 레벨 스위처로 전환

## 이중 언어 콘텐츠 모델

각 용어는 EN/KO 양쪽으로 3단계 필드를 가진다:

| 필드 | EN | KO | 용도 |
|---|---|---|---|
| **definition** | `definition_en` | `definition_ko` | 한 줄 정의 (팝업, 카드) |
| **body_basic** | `body_basic_en` | `body_basic_ko` | 기초 설명 본문 (마크다운) |
| **body_advanced** | `body_advanced_en` | `body_advanced_ko` | 심화 설명 본문 (마크다운) |

### Fallback 규칙

- EN 값이 비어 있으면 KO fallback 허용
- Fallback 시 "translation pending" 안내를 표시
- KO → EN fallback은 적용하지 않음

### 필드 선택 로직

```ts
const definition = localField(term, 'definition', locale);
const bodyBasic = localField(term, 'body_basic', locale);
const bodyAdvanced = localField(term, 'body_advanced', locale);
```

## Naming Convention

| Context | 사용 용어 |
|---|---|
| **공개 제품 UI** | AI Glossary |
| **내부/Admin** | Handbook |
| **Route** | `/{locale}/handbook/` |

> [!note] 일관성
> 공개 페이지에서는 "AI Glossary"로 표기하고, 코드/Admin에서는 "Handbook"을 사용한다.

## Definition-First 원칙

- 상세 페이지: `definition`을 ==가장 먼저== 노출
- Handbook popup (뉴스/블로그 본문 내): `definition`만 표시
- 팝업에 장문 본문을 넣지 않음 — 빠른 정의 확인 후 상세 페이지로 이동시키는 구조

## Feedback 모델

| 반응 | 의미 | 활용 |
|---|---|---|
| `helpful` | 설명이 이해에 도움 됨 | 긍정 신호 |
| `confusing` | 설명이 헷갈림 | ==보완 우선순위== 수집 근거 |

- Authenticated user only
- Locale별 별도 수집 (같은 용어라도 EN/KO 각각 반응 가능)
- Admin에서 `confusing` 비율 높은 용어를 우선 보완

## 작성 가이드라인

### definition 작성
- 한 문장으로 핵심 의미를 전달
- 팝업에서도 읽히도록 간결하게
- 전문 용어 남용 지양

### body_basic 작성
- 비유, 예시 중심
- 전문 지식 없이 이해할 수 있는 수준
- 마크다운 포맷 활용 (리스트, 코드 블록 등)

### body_advanced 작성
- 기술적 정의, 구조 설명
- 실무 관점의 사용 사례
- 코드 예시, 아키텍처 다이어그램 포함 가능

## Related

- [[Content-Strategy]] — 상위 콘텐츠 전략
- [[Global-Local-Intelligence]] — 다국어 운영 전략

## See Also

- [[Handbook]] — Handbook 기능 상세 (03-Features)
