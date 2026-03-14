---
title: AI News Page Layouts
tags:
  - design
  - visual
  - tier-2
source: [docs/02_Content_Strategy.md, docs/04_Frontend_Spec.md]
---

# AI News Page Layouts

뉴스 페이지의 시각적 요소 + 인터랙션 디자인.

## 뉴스 '온도' 시각화 (Phase 2)

뉴스의 혁신 정도를 시각적으로 표현:

| 등급         | 스타일         | 설명            |
| ---------- | ----------- | ------------- |
| **매우 혁신적** | 강조 + 불꽃 아이콘 | 파격적 뉴스에 시선 집중 |
| **일반**     | 기본 스타일      | 평소 디자인 유지     |

## 타임라인 인디케이터 (Phase 3)

해당 기술의 역사(History) 중 현재 위치를 보여주는 프로그레스 바.

- 초기 연구 → 실험 → 상용화 단계 표시
- 예: "LLM 추론 최적화" 기술이 어느 단계인지 시각화

## Highlight to Share (Phase 3)

본문 드래그 → SNS 공유 버튼 팝업 (바이럴 장치).

- 드래그한 문장 + 블로그 링크 포함 카드 자동 생성
- 대상 플랫폼: X(Twitter), LinkedIn
- 공유 시 20pt 지급 ([[Community-&-Gamification|포인트 시스템]] Phase 4 연동)

## Home

`/` — 랜딩 페이지.

- **Hero Section**: "0 → 1 log" 타이포그래피 애니메이션 (Clash Display, 글자별 staggered fade-in) + 서브카피 "AI Engineer's Journey" 타이핑 효과
- **Today's AI Pick**: 매일 자동 생성되는 Research + Business 2장 카드
  - 제목, 한줄 요약, 온도 배지 (불꽃 아이콘 개수), 태그
  - 카드 호버 시 accent 보더 glow
- **Recent Posts**: 최근 글 8개 그리드 (카테고리 필터 탭 포함)
- **Search shortcut**: `Cmd+K` 검색 모달 진입 — Phase 3 전까지 키워드 검색, 이후 시맨틱 검색으로 업그레이드

## Log (글 리스트)

`/log` — 전체 포스트 목록.

- **카테고리 필터**: All / AI NEWS / Study / Career / Project — 탭 형태, 활성 탭에 accent 언더라인 애니메이션
- **정렬**: 최신순 기본
- **Post Card 구성**:
  - `post_type` 아이콘 (Research / Business)
  - 카테고리 배지, 제목 + `one_liner` 미리보기
  - 뉴스 온도 (카드 좌측 얇은 컬러 바)
  - 읽기 시간, 발행 시간, 태그
- **페이지네이션**: Load More 버튼 (무한 스크롤 가능)

## Post Detail

`/log/[slug]` — 개별 포스트.

### Research 포스트

마크다운 렌더링 + 코드 블록 (Shiki 하이라이팅). 단일 기술 심화 구조:

- The One-Liner → 본문 → Action Item → Critical Gotcha → 회전 항목 → Today's Quiz → Sources → Comments

### Business 포스트

5블록 구조로 비즈니스 뉴스를 다각도로 분석:

1. **Executive Summary** (The One-Liner)
2. **Deep Dive** (본문 — 페르소나별 전환)
3. **Action Items**
4. **Critical Gotchas**
5. **Related News** — Big Tech / Industry & Biz / New Tools 3개 카테고리, 각각 아이콘 + 한줄 요약

> [!note] 모바일 UX
> 태블릿/모바일에서는 블록 아코디언 접기/펼치기로 긴 콘텐츠를 관리한다.

### Persona Switcher (Business only)

- Business 포스트 상단에만 노출 (Research에서는 렌더링하지 않음)
- 3개 탭: 입문자 / 학습자 / 현직자
- 전환 시 본문 영역만 crossfade 애니메이션 (전체 리로드 없음)
- 기본 선택: 쿠키에 저장된 페르소나

### 읽기 인디케이터

본문 `<article>` 영역 기준 읽기 진행률 + 남은 시간 표시. 댓글/Related News/Footer는 진행률에서 제외.

| 화면 폭 | 형태 | 이유 |
| --- | --- | --- |
| 1024px+ (데스크탑) | 우측 세로 레일 프로그레스 + 남은 시간 | 본문 720px + 좌우 여백 충분 |
| 768~1023px (태블릿) | 하단 슬림 바 (40px) | 본문 넣으면 우측 여백 부족 |
| ~767px (모바일) | 하단 슬림 바 (40px) | 동일 |

> [!important] 상단 바 대신 이 방식을 쓰는 이유
> 상단 2px 바는 전체 페이지 스크롤 기준이라 본문 끝을 알 수 없고, 퍼센트만으로는 심리적 동기가 약하다. "~3min left"라는 남은 시간 정보가 "조금만 더 읽자"는 동기를 만든다.

### 5-Block Prompt Guide

Business 포스트 각 블록에 설명 표시 — 독자가 구조를 이해하도록 안내.

### Comment & Feedback

- Comment Section (하단)
- Feedback Widget: "도움이 되었나요?" 좋아요 / 싫어요

## Portfolio

`/portfolio` — 프로젝트 포트폴리오.

- **프로젝트 케이스 스터디**: 문제 → 설계 → 결과 측정 카드 형태
- **아키텍처 다이어그램**: 0to1log 파이프라인 인터랙티브 시각화 (Tavily → Ranking → Research/Business → Editorial → Supabase)
  - 노드 호버 시 설명 툴팁, accent 연결선 + 데이터 흐름 애니메이션

## Admin

`/admin` — 관리자 대시보드.

> [!note] Phase 1 → Phase 2 진행
> Phase 1에서는 에디터를 최소화한다. AI 파이프라인이 없는 Phase 1에서는 수동 포스트 몇 개만 작성하면 되므로 Supabase Dashboard에서 직접 편집하는 것으로 충분하다. Phase 2에서 에디터를 한 번에 제대로 만들어 이중 개발을 방지한다.

### Phase 1 (최소)

- 글 목록 (제목, status, 발행일)
- status 변경 드롭다운: `draft → published → archived`
- 삭제 버튼 (확인 모달)
- "새 글" → Supabase Dashboard 외부 링크

### Phase 2 (풀 에디터)

- **DraftList**: 글 목록 + 상태 관리
- **PostEditor**: 좌측 마크다운 편집창 (메타데이터 + 본문)
- **실시간 미리보기**: 우측 상단 — 페르소나 탭 전환 가능
- **AIPanel**: 우측 하단 — Editorial 피드백 + 수정 제안 클릭 반영
  - AI 초안 생성 / 검수 / 재작성
  - 호출 경로: `FastAPI /api/admin/ai/*` 경유
- **PipelineStatus**: 파이프라인 상태 모니터링

## Related

- [[Component-States]] — 컴포넌트 상태 정의
- [[Frontend-Stack]] — 페이지가 동작하는 프레임워크
- [[Content-Strategy]] — 시각 요소가 서비스하는 콘텐츠 전략
- [[Gamification-UI]] — 포인트/뱃지 시각화 디자인
- [[Design-System]] — 디자인 시스템
- [[Mobile-UX]] — 모바일 UX 패턴
- [[Animations-&-Transitions]] — 애니메이션 및 트랜지션
