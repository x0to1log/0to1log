---
title: Vault 운영 규칙
tags:
  - meta
---

# Vault 운영 규칙

> 이 문서는 vault에 노트를 추가하거나 수정할 때 따라야 할 규칙을 정의한다.
> 그래프 품질 유지와 일관성 있는 노트 구조가 목적.

---

## 1. 레이어 구조

| 번호 | 레이어 | 용도 |
|------|--------|------|
| 00-Root | 대시보드, 메타 문서 | INDEX, 스프린트 현황, 마이그레이션 로그 |
| 01-Core | 비전, 로드맵, 오디언스 | 프로젝트의 "왜"와 "누구를 위해" |
| 02-Architecture | 시스템 설계, 스택 | 기술 아키텍처, DB 스키마, API |
| 03-Features | 제품 기능 | 뉴스, 핸드북, Admin, 커뮤니티 |
| 04-AI-System | AI 파이프라인, 프롬프트 | 에이전트, 품질 게이트, 콘텐츠 생성 |
| 05-Content | 콘텐츠 전략, 작성 규칙 | 글로벌-로컬, 페르소나 톤 |
| 06-Business | 비즈니스 전략, KPI | 수익화, 그로스, SEO |
| 07-Operations | 인프라, 배포, 비용 | Railway, Vercel, 모니터링 |
| 08-Design | UI/UX 패턴 | 디자인 시스템, 컴포넌트, 접근성 |
| 09-Implementation | 스프린트, 체크리스트, 계획 | 실행 문서 + `plans/` 하위 폴더 |
| 90-Archive | 아카이브 | 폐기/교체된 노트 보관 |

> [!warning] 새 레이어 추가 금지
> 기존 레이어에 맞지 않는 노트는 가장 가까운 레이어에 배치하거나, 이 문서를 먼저 업데이트한다.

---

## 2. 노트 구조 템플릿

```markdown
---
title: 노트 제목
tags:
  - 레이어명 (예: features, ai-system)
---

# 노트 제목

> 한 줄 요약 또는 메타데이터 (상태, 날짜 등)

---

## 본문 섹션들

(내용)

## Related

- [[Same-Layer-Note-A]] — 간단 설명
- [[Same-Layer-Note-B]] — 간단 설명

## See Also

- [[Cross-Layer-Note]] — 간단 설명 (레이어명)
```

---

## 3. 링크 규칙 (그래프 클러스터 유지)

> [!important] 핵심 원칙
> **같은 레이어 우선, 다른 레이어 최소화.** 이것이 그래프 클러스터를 만든다.

### `## Related` — 같은 레이어 내 링크

- **같은 폴더**에 있는 노트만 링크
- 2~3개 권장, 최대 4개
- 클러스터 형성의 핵심

### `## See Also` — 다른 레이어 링크

- **다른 폴더**에 있는 노트 링크
- **최대 2개** (가장 중요한 의존성만)
- 레이어명을 괄호로 표기: `(02-Architecture)`

### 본문 내 링크

- 본문에서 다른 노트를 참조할 때는 wikilink 사용 가능
- 단, 본문 내 링크는 **설명 맥락**에서만 (목록으로 나열하지 않음)
- 본문 내 cross-layer 링크는 그래프에 반영되므로 필요한 경우만 사용

### 금지 사항

- Related에 다른 레이어 노트 넣지 않기
- See Also에 3개 이상 넣지 않기
- 00-INDEX에서 직접 노트를 추가하지 않기 (Navigation 테이블만 유지)

---

## 4. Plan 파일 규칙

### 위치

`09-Implementation/plans/YYYY-MM-DD-<slug>.md`

### 링크 규칙

- `## Related Plans` — **다른 plan 파일만** wikilink
  - 형식: `[[plans/YYYY-MM-DD-slug|표시명]]`
  - 같은 기능의 design↔impl, 진화 관계(v1→redesign) 연결
- 지식 노트 참조 → **backtick** 사용 (그래프에 안 보임)
  - 예: `vault/04-AI-System/AI-News-Pipeline-Design.md`
- **지식 노트에 wikilink 금지** → plan 클러스터 독립 유지

### 예시

```markdown
# Feature X — 설계

> 관련: `vault/03-Features/Feature-X.md`

(본문)

## Related Plans

- [[plans/2026-03-15-feature-x-impl|Feature X 구현]]
```

---

## 5. 네이밍 규칙

| 유형 | 형식 | 예시 |
|------|------|------|
| 지식 노트 | `Title-Case-Hyphens.md` | `AI-News-Pipeline-Design.md` |
| Plan 파일 | `YYYY-MM-DD-slug.md` | `2026-03-15-news-pipeline-v2-impl.md` |
| 스프린트 | `ACTIVE_SPRINT*.md` | `ACTIVE_SPRINT.md` |
| 메타 문서 | `UPPER_CASE.md` | `VAULT_RULES.md` |

---

## 6. 새 노트 추가 체크리스트

> [!todo] 노트 추가 시 확인 사항
> - [ ] 올바른 레이어 폴더에 배치했는가?
> - [ ] frontmatter에 `title`과 `tags`가 있는가?
> - [ ] `## Related`에 같은 레이어 노트 2~3개를 링크했는가?
> - [ ] `## See Also`에 다른 레이어 노트가 **2개 이하**인가?
> - [ ] Related에 넣은 대상 노트에서도 이 노트를 역으로 링크했는가? (양방향)
> - [ ] Plan 파일이면 `## Related Plans`만 사용하고 지식 노트 wikilink는 없는가?

---

## 7. 그래프 설정

`vault/.obsidian/graph.json`에 path 기반 색상 그룹 설정됨:

| 레이어 | 색상 |
|--------|------|
| 01-Core | 빨강 |
| 02-Architecture | 파랑 |
| 03-Features | 초록 |
| 04-AI-System | 보라 |
| 05-Content | 주황 |
| 06-Business | 노랑 |
| 07-Operations | 청록 |
| 08-Design | 핑크 |
| 09-Implementation/plans | 회색 |
| 09-Implementation | 연보라 |
| 00-Root | 흰색 |
