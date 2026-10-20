# ACTIVE SPRINT — 뉴스 파이프라인 GPT-6 전환 + 운영 안정화 (NP-GPT6)

> **스프린트 기간:** 2026-10-13 ~ 진행 중
> **마지막 업데이트:** 2026-10-19 (보드 재정의: HB-QM 보류 종료 → NP-GPT6. 전 역할 GPT-6 전환 완료, 관찰 기간 시작)
> **목표:** 2026-12-11 종료되는 gpt-5 계열을 GPT-6로 교체하고, 전환 과정에서 드러난 운영 결함(조용한 중단, QC 근거 부족, 퀴즈 오답, 프롬프트 유도 과장)을 정리해 자동 발행을 안정화
> **이전 스프린트:** [[2026-10-19-hbqm-sprint-close|HB-QM]] (보류 종료 2026-10-19)
> **설계 참조:** [[2026-10-13-news-pipeline-gpt6-upgrade]] (단일 기록), [[2026-10-15-news-prompt-revision]], [[2026-10-15-frontload-claim-grounding]]

---

## 스프린트 완료 게이트

- [x] **운영 gpt-5 계열 사용 0** — main/reasoning=gpt-6.1-sol, light/nano=gpt-6-luna (`88ebb50c` 10-15, `78328166` 10-19)
- [ ] **관찰 통과** — 전환 후 daily 5회 + 첫 sol 작성 weekly(10-26) 정상: 실행 성공, gate 판정이 의도대로, draft 원인 분류 완료
- [ ] **gpt-5 잔재 정리** — 가격표 gpt-5 항목, A/B 스크립트 gpt-5 조합, 테스트 픽스처의 gpt-5 기본값 정리
- [ ] **최종 검증** — `ruff check .` (변경 파일) + `pytest tests/` 통과, frontend `npm run build` 성공

---

## Current Doing (active work only)

> **운영 규칙:** Current Doing은 **active work만** 추적. done은 즉시 제거. 14일 + 매칭 커밋 0 = ghost → drop or restart 결정.

| Task ID | 제목 | 상태 | 시작 | 예상 완료 |
|---|---|---|---|---|
| NP-GPT6-OBSERVE | 전환 관찰: daily 10-20~10-25 (자동 발행, draft 원인, luna 분류·순위 결과의 기사 수·주제, 퀴즈 검증 빈도, 비용) + 10-26 첫 sol 작성 weekly | doing | 2026-10-19 | 2026-10-26 |
| RECOVERY-01 | 09:00 복구 확장: run 없음 / rank 이전 실패 / 뉴스 0건 → 전체 실행 1회 + 승격 — [[2026-10-20-daily-run-recovery]] | doing | 2026-10-20 | 2026-10-21 |

---

## 이번 스프린트 완료

### GPT-6 전환 + 파이프라인 안정화 — 2026-10-13 ~ 2026-10-19

> **기록:** [[2026-10-13-news-pipeline-gpt6-upgrade]] (Phase 0~1 상세, 측정 수치, 결정 근거)

- [x] **NP-OUTAGE-01** — 09-29~10-11 자동 실행 중단 원인 = Supabase 일시정지 (cron 아님). 복구 + 수동 실행, 10-14 자동 실행 정상 확인
- [x] **NP-HEALTH-01** — admin 대시보드 실행 누락·연속 실패 감지 (cron 일정 대비, 원인 분류) — `fe5ce918`. 외부 알림 없음 (Amy 결정)
- [x] **GPT6-1.1** — reasoning 모델 판정 일반화 (`gpt-N`, N≥5) — `4747ad5f`
- [x] **GPT6-1.2** — GPT-6 파라미터 probe (flex·json_schema·cache key 전부 지원) — `cae0a93e`
- [x] **GPT6-1.3** — 가격표 수정 (gpt-5 $2/$8 오류 → $1.25/$10) + 모델별 캐시 가격 — `b803b962`
- [x] **GPT6-1.4** — 비파괴 A/B·재채점 도구 (checkpoint replay + 가짜 Supabase, `--rescore`, `--rescore-dates`, `--rescore-weeks`) — `cc28a156`, `1b1551cb`, `06ae3d3c`, `1ac43393`
- [x] **GPT6-1.6** — 퀴즈 정답 검증 단계 (교정·재생성·제외) — `cef60858`. 운영 감사 스크립트 `79004e0c`
- [x] **GPT6-1.7** — auto-publish gate: 차단 cap 이름 기반 + score ≥ 70 — `1a1a0b1f`
- [x] **GPT6-1.7a** — QC frontload 근거 발췌 개선 (claim 수치·%, 고유명사, 겹치는 단어, 밀집 창) — `1c5f142e`, `6855619e`, `6991ae1b`
- [x] **GPT6-1.5a** — reasoning 전환 (QC judge sol + threshold 70) — `88ebb50c` (10-15 Railway 변수로 인한 반쪽 전환 사고 포함, 이후 Railway 모델 변수 전부 삭제 → `config.py` 단일 출처)
- [x] **GPT6-1.5** — main sol / light·nano luna 전환 — `78328166`. A/B: 평균 81.3 → 90.5, 비용 -15%
- [x] **PROMPT-REV-01** — 뉴스 프롬프트 개정 (날짜 블록, EN frontload 점검, focus P2 예시 교체, KO 수량 한정어, QC 반올림 수치) — `7acbc069`, `5ec5dc70`. A/B: 차단 4/4 → 1/4
- [x] **CONTENT-FIX** — 발행 콘텐츠 수정: 09-25 KO beginner 퀴즈 정답, 09-28 "former President" (draft)

- [x] **QC-DATE-01** — QC judge에 KST digest 날짜 제공 (writer만 날짜를 받던 비대칭 → "as of" 표기가 미래 시점으로 오판, 10-20 business draft). 재채점 82+cap → 91

**운영 결과 (전환 후):** 10-17·10-18 daily 4/4 자동 발행, 10-19 W42 weekly 자동 발행, 차단 cap 0건, 퀴즈 검증 2건 교정·1건 제외

### 사이트 리디자인 1단계(기반) — 2026-10-14

> **계획:** [[2026-10-14-site-redesign-phase1-foundation]] / **설계:** [[2026-10-14-site-redesign-soft-newsprint-design]]
> **commits:** `ffac2fb0..0448f82a` (main, 18개). `8e0c72a4`까지 push·배포됨, `0448f82a`는 로컬

- [x] **REDESIGN-P1** — 테마 3종(light 종이 / white / dark, pink·midnight 폐기 + 저장값 마이그레이션, `src/lib/theme.js` 단일 소스) + 글꼴 체계(Newsreader / Hahmlet / Pretendard) + 레트로 장식 제거(드롭캡, 이중 룰, 노이즈, 대문자 kicker)
  - **증거:** 전체 테스트 54 PASS / 23 FAIL (23개 전부 기준선의 기존 실패, 신규 실패 0), `npm run build` 에러 0, 브라우저 확인 (/ko/, /ko/news/, 뉴스 기사, 핸드북 용어, 블로그 글 x 3테마 + 375px 모바일), pink→light·midnight→dark 마이그레이션·토글 순환 확인, CSP 콘솔 에러 없음
  - **후속:** 계획 문서 "실행 결과"의 후속 작업 목록 참조 (no-dropcap 클래스 제거, `.admin-*` faux italic, Pretendard 800 정리, `--color-cat-*` 삭제, 모바일 홈 히어로 제목 크기 → 3단계)
- [x] **REDESIGN-P2** — 공통 헤더·푸터 (A안: 한 줄 헤더 + 점 줄, 제호 주황 마침표, 현재 메뉴 주황 점, 푸터 점 줄 + 모토) + 페이지 제호 키커 호수 자동 계산(`src/lib/issue.js`, ISSUE_EPOCH 2026-03-18, `volume_issue` 설정 제거) — [[2026-10-14-site-redesign-phase2-header]]
  - **증거:** 커밋 ff46a639..fc033759, 전체 테스트 57 PASS / 23 FAIL (실패 목록 1단계와 동일, 신규 실패 0), `npm run build` 에러 0, 브라우저 확인 (/ko/news/ 종이·다크 x 1280px·375px, 헤더 숨김 시 점 줄 잔상 없음, 재노출, 게스트 메뉴 "로그인"만 표시, 키커 제211호, 푸터)
  - **후속(P2):** 목록의 sticky 검색창 배경이 투명해 헤더 아래로 본문이 비침(3월부터의 기존 동작) → 5단계, DB `site_content.volume_issue` 행 정리
- [x] **REDESIGN-P3** — 홈: Hero V2(큰 제호 `0to1log.`, 모토, 호수 줄 + 오늘 N건) + "오늘의 1면"(머리기사 + 같은 날 한 줄 + 오늘의 용어) — [[2026-10-14-site-redesign-phase3-home]], 결정 [[2026-10-14-homepage-front-strip]]
  - **증거:** 커밋 23423a90..1fad2005, 전체 테스트 61 PASS / 23 FAIL (실패 목록 1단계와 동일, 신규 실패 0), `npm run build` 에러 0, 브라우저 /ko/ 종이·다크 × 1280px·375px, /en/ 문구 확인, 오늘의 용어 표시 확인
  - **발견·수정:** DB에 즐겨찾기 용어 0개 → 오늘의 용어를 발행 용어 전체에서 1행 조회로 변경(82fc1d1c), 주간 리캡 라벨(1fad2005)
- [x] **REDESIGN-P4** — 뉴스 기사: 판 선택(입문판·학습판·전문판, 점 표시), 기사 머리(카테고리 점·태그 위치·제목), 섹션 제목, 핵심 팩트 점선 목록, 기존 용어 하이라이트 형광펜 재스타일, 레일 "이 기사의 용어", 퀴즈·출처 — [[2026-10-15-site-redesign-phase4-article]]
  - **증거:** 커밋 4957ce17..a6df5abb, 전체 테스트 63 PASS / 23 FAIL(신규 실패 0), `npm run build` 성공, 브라우저 기사 페이지 종이·다크 × 데스크톱·모바일, 판 전환(제목·본문·플로팅 버튼), 용어 팝업, 게스트 관리자 블록 숨김, 댓글·좋아요·북마크 훅 확인
  - **결정:** 2단 유지, 번호 사이드노트 미적용(사용자 선택). 블로그 판 스위처도 같은 스타일 공유(의도). **후속:** 목록 카드의 research/business 라벨 색 구분 → 5단계
- [x] **REDESIGN-P5** — 뉴스 목록: 점선 카드, 유형 라벨 단일화(`lib/postType.js`, 주간 정리→"Business" 버그 수정), 카테고리 inline 색 제거, 탭 점 표시, `#태그`(뉴스 범위), 머리기사, 레일 "최신 기사"+번호, 고정 검색창 배경 — [[2026-10-15-site-redesign-phase5-news-list]]
  - **증거:** 커밋 dbf7e0c4..c65244d3, 전체 테스트 66 PASS / 23 FAIL(신규 실패 0), `npm run build` 성공, 브라우저 /ko/news/ 다크 — 탭 필터(비즈니스 49/리서치 51/주간 19)와 머리기사 라벨, 검색(Gemini 21건), 레일 번호, 블로그 목록 영향 없음
  - **같은 날 성능 수정(Supabase 세션 요청):** Pretendard dynamic subset(c65abc36, 운영 기사 첫 방문 3,260KB→625KB), Hahmlet 400 제거(b309a9cc), hreflang 짝 slug(f655c620)
  - **해결된 후속:** 투명한 고정 검색창(P2), research/business 구분(P4). **남은 후속:** `list-rail-copy` 테스트 낡은 문구, `--tab-cat-color` 미사용 변수
- [x] **REDESIGN-P6** — 핸드북: 사전 항목(카드 제거·함렛 용어·정의 2줄·점선), 분야 필터 점 탭(한 줄 가로 스크롤), 많이 찾는 용어 번호 목록(중복 CSS 블록 제거), 분야별 점선 목록(`#handbook-showcase` 범위), 상세 머리·한 줄 정의 박스·수준 선택 점·관련 용어 점선·대문자 라벨 제거 — [[2026-10-15-site-redesign-phase6-handbook]]
  - **증거:** 커밋 41b988d8..9f98062c, 전체 테스트 67 PASS / 23 FAIL(신규 실패 0), 빌드 성공, 브라우저 /ko/handbook/ 필터(LLM·생성AI)·사전 항목, BM25 상세 수준 전환(기초→심화)·게스트 학습 버튼·관리자 블록 숨김·관련 용어 6개
  - **참고:** 관리자 핸드북 목록도 `.handbook-card`를 공유해 점선 구분선이 생김(무해)
- [x] **REDESIGN-P7** — 블로그: 카테고리 색은 점에만(B안), 평평한 사이드바 + 점선 트리(모바일 드로어 불투명 배경 유지), 폴더 카드 줄 → 카테고리 탭 + 문구, 추천·목록 칼럼 항목, 글 머리(📘 제거·카테고리 점 라벨), 목차 제목 정리 — [[2026-10-15-site-redesign-phase7-blog]]
  - **증거:** 커밋 6e3bad16..84ec9daf, 전체 테스트 68 PASS / 23 FAIL(신규 실패 0), 빌드 성공, 브라우저 /ko/blog/·글 상세·모바일 드로어, 댓글·좋아요·읽기 기록·관리자 숨김 훅 확인
  - **브라우저에서 발견·수정:** 추천 카드 태그 "##" 중복, 글 메타가 코드 글꼴(JetBrains Mono)이라 한글 자간이 벌어짐 → Pretendard
- [x] **REDESIGN-P8a** — 제품: 가격·난이도 등급 색은 점에만(B안, `--tier-*` 토큰·다크 재정의), 카테고리 타일·카드 평평하게(그라디언트 대체 썸네일 → 은은한 면 + 로고), 장단점 ＋/−, 번호 원 제거, 사이트 방문 버튼 먹색, 미사용 Spotlight CSS 삭제 — [[2026-10-15-site-redesign-phase8a-products]]
  - **증거:** 커밋 1be1ef86, products-v2 테스트, 기존 product 테스트(찜하기·관리자·검색 sticky) 통과, 빌드 성공, 브라우저 /ko/products/·/ko/products/dify/ 종이·다크
- [x] **REDESIGN-P8b** — 기타 페이지: about(대문자 overline·원 번호·태그 칩 정리), 404 버튼, 서재 탭 → 점 탭·진행 막대 단색, 포트폴리오 800/대문자/inset 그림자 정리, 설정 대문자 라벨 정리 — [[2026-10-15-site-redesign-phase8b-misc-pages]]
  - **모바일 보정:** 영문 메뉴 줄바꿈, 제품 타일 이중 스크롤(→ 4개 + 전체 보기), 검색창 아래 이중 선 — [[2026-10-15-site-redesign-mobile-polish]]
- [x] **REDESIGN-HOME** — 홈을 신문 1면(A안)으로 재설계: 마스트헤드 h1 + 날짜줄 + 3단 지면(지난 지면 / 1면 + 키워드 판 / 오늘의 용어), 소개 문구는 맨 아래 안내로 — [[2026-10-15-home-front-page-redesign-design]], [[2026-10-15-home-front-page-redesign]]
  - **증거:** 커밋 0634c4d4, efaf2385, c4b3658e, 전체 테스트 70 PASS / 23 FAIL(신규 실패 0), 빌드 성공, 브라우저 3테마 × 데스크톱·모바일 × ko/en (가로 넘침 0, 대비 미달 0)
- [x] **REDESIGN-NEWS-LIST** — 뉴스 목록을 두 데스크 지면(E안)으로: 비즈니스 | 날짜 축 | 리서치, 주간 정리 먹색 띠, 탭·검색 시 한 단 목록, 오른쪽 레일·해시태그 줄 제거 — [[2026-10-16-news-list-desks-design]], [[2026-10-16-news-list-desks]]
  - **증거:** 커밋 0c1998c6, d1da3176, 98073b31, 신규 FAIL 0, 빌드 성공, 탭·검색·직접 URL 클릭 검증, 3테마 × 데스크톱·모바일 × ko/en (가로 넘침 0, 대비 미달 0)
- [x] **REDESIGN-NEWS-ARTICLE** — 기사 상세를 한 단 지면(B+C)으로: 경로 줄(대형 마스트헤드 제거), 같은 날 다른 데스크 링크, 판 선택 → 30초 브리핑, 본문 옆 세로 액션 막대, 끝 블록(용어·두 데스크의 시선·다음 글), 오른쪽 레일·TOC 제거 — [[2026-10-16-news-article-briefing-design]], [[2026-10-16-news-article-briefing]]
  - **증거:** 커밋 bf1ad057, a731ff17, c7434af5, d6c43843, 신규 FAIL 0, 빌드 성공, 판 전환·용어 팝업·본문 찾기·공유·짝 링크 클릭 검증, 3테마 × 데스크톱·모바일 × ko/en × 비즈니스/리서치/주간 (가로 넘침 0, 대비 미달 0)
- [x] **REDESIGN-HANDBOOK-INDEX** — 용어집 첫 화면을 오늘의 용어(홈과 공유 쿼리) + 분야별 서가 + A–Z 색인으로: 114개를 첫 화면에서 바로 탐색, 인기 10·분야 버튼·오른쪽 레일 제거, `?category=` 해제 링크 — [[2026-10-17-handbook-index-shelves-design]], [[2026-10-17-handbook-index-shelves]]
  - **증거:** 커밋 9449bfef, b934d453, 85b46b99, 61183a8d, 신규 FAIL 0, 빌드 성공, 검색·분야 주소·색인 이동 클릭 검증, 홈과 오늘의 용어 일치, 3테마 × 데스크톱·모바일 × ko/en (가로 넘침 0, 대비 미달 0)
- [x] **REDESIGN-HANDBOOK-TERM** — 용어 상세를 사전 표제어(A) + 개념 지도(B)로: 경로 줄(분야), 큰 표제어·풀네임·품사 줄(유형·쓰임·변화 정도), 정의 + 뉴스 판, 함께 볼 말(편집 순서), 세로 액션 막대, 끝 블록 개념 지도·최근 뉴스(실제 언급만), 레일·목차 제거 — [[2026-10-17-handbook-term-entry-design]], [[2026-10-17-handbook-term-entry]]
  - **증거:** 커밋 aefdee45, 40d68023, 7ab1c1b8, 647deae5, 92b4b367, 신규 FAIL 0, 빌드 성공, 레벨 전환·팝업·저장·공유·지도 링크 클릭 검증, 3테마 × 데스크톱·모바일 × ko/en (가로 넘침 0, 대비 미달 0, 지도 잘림 0)
- [x] **REDESIGN-BLOG-LIST** — 블로그 목록을 연재 칼럼(A)으로: 바이라인(필자·편수·마지막 글)·검색, 최신 글 + 연재 수, 연재(카테고리 = 연재, 발행 순 회차), 짧은 글, 목록에서 사이드바·대표 카드·탭 제거 — [[2026-10-17-blog-list-serial-design]], [[2026-10-17-blog-list-serial]]
  - **증거:** 커밋 e6b0c0a9, 36937103, e3cc40ee, 신규 FAIL 0, 검색·연재 링크·저장 버튼·회차 순서 클릭 검증, 3테마 × 데스크톱·모바일 × ko/en (가로 넘침 0, 대비 미달 0), 카테고리·글 상세 회귀 정상
- [x] **REDESIGN-BLOG-POST** — 블로그 글 상세를 칼럼 한 편(A)으로: 경로 줄(IT 블로그 · 분야 · n화), 제목·요약, 바이라인(Amy · 연도 포함 날짜 | 분야 · N편 중 n화), 접는 차례, 인라인 세로 액션 막대, 끝 블록 이전·다음 화·연재 목록, 폴더 트리·오른쪽 레일 제거, 거꾸로 가던 다음 글 쿼리 제거 — [[2026-10-17-blog-post-column-design]], [[2026-10-17-blog-post-column]]
  - **증거:** 커밋 793afbba, fd393dc4, d4fcb440, 신규 FAIL 0, 빌드 성공, 차례·저장·공유·용어 팝업·이전/다음·연재 링크 클릭 검증, 3테마 × 데스크톱·모바일 × 2화·1화·5화·짧은 글 (가로 넘침 0, 대비 미달 0), 분야 페이지·뉴스 상세 회귀 정상
- [x] **REDESIGN-PRODUCTS** — AI 제품군 목록을 분야 카탈로그(A)로: h1 + 개수·검색, 분야 바로가기, 편집자 추천 5칸(노트 첫 문장), 분야별 3열 6개 + 모두 보기(보조 분야 도구 포함), 타일 안 스크롤·이중 렌더 제거, 노트는 추천 5개만 따로 조회 — [[2026-10-18-products-catalog-design]], [[2026-10-18-products-catalog]]
  - **증거:** 커밋 267a792d, ee88786e, 996d6c37, 신규 FAIL 0, 빌드 성공, 모두 보기·돌아가기(포커스)·`?cat=` 진입·검색·결과 없음·Enter 클릭 검증, 3테마 × 1100·900·375px × ko/en (가로 넘침 0, 대비 미달 0), 제품 상세 회귀 정상
- [x] **REDESIGN-PRODUCT-DETAIL** — 제품 상세를 리뷰 지면(A)으로: 경로 줄(AI 제품군 · 분야), 이름·한 줄 소개 + 스펙 상자(가격·난이도·플랫폼·한국어·방문·찜), 에디터 한마디 인용, 장단점 좌우, 시나리오 3개 + 더 보기, 기능·상황 2단, 가격표, 끝 블록(뉴스·비슷한 도구 줄·FAQ), 상단 검색·하단 큰 CTA 제거, 모바일 하단 고정 버튼 바, 비슷한 도구 원래 이름 — [[2026-10-18-product-detail-review-design]], [[2026-10-18-product-detail-review]]
  - **증거:** 커밋 3d697589, 12e2f1b0, 12475893, 신규 FAIL 0(scenarios-theme FAIL→PASS), 빌드 성공, 찜·방문·시나리오·FAQ·경로 줄 클릭 검증, 3테마 × 데스크톱·모바일 × chatgpt·flowise·grok·en (가로 넘침 0, 대비 미달 0, 하단 바가 푸터 안 가림), 목록 회귀 정상
- [x] **REDESIGN-BLOG-CATEGORY** — 블로그 분야 페이지를 연재 목차(A)로: 경로 줄(IT 블로그 · 연재/짧은 글), 분야 이름, 바이라인(연재 N편 · 기간 | 1화부터 읽기), 발행 순 회차 목록 + 요약, 다른 분야 줄, 빈 안내, 조회 실패 503, 숨김 분야 404, 목록·상세와 같은 100편 쿼리로 회차 일치, 블로그 사이드바 완전 제거(BlogShell 한 단 고정) — [[2026-10-18-blog-category-toc-design]], [[2026-10-18-blog-category-toc]]
  - **증거:** 커밋 04985ba2, 38030e5c, 73fe590b, 신규 FAIL 0, 빌드 성공, 1화부터 읽기·저장·다른 분야·404 확인, 회차가 목록·상세와 일치, 3테마 × 데스크톱·모바일 × study·work-note·career·en (가로 넘침 0, 대비 미달 0), 목록·상세 회귀 정상
  - **증거:** 커밋 27e00b48, 67463620, 전체 테스트 70 PASS / 23 FAIL(신규 실패 0, 실패 목록 동일), 빌드 성공, 브라우저 /ko/about/·/library/·/portfolio/·404


---

## NP-GPT6 남은 태스크

### HIGH — 관찰 후 정리

| Task | 상태 | 목표 |
|------|------|------|
| NP-GPT6-CLEANUP | todo (관찰 후) | `OPENAI_MODEL_PRICING_PER_1M` gpt-5 항목, `ab_daily_models.py` baseline/prod 조합, 테스트의 gpt-5 문자열 정리. 롤백 가능성 때문에 관찰 기간에는 유지 |
| FRONTLOAD-GROUND-01 | todo | Phase 1: frontload 수치·이름 근거 검사 (감지만, 로그) → 1주 오탐률 측정 → Phase 2 수리 — [[2026-10-15-frontload-claim-grounding]] |
| QC-EVIDENCE-03 | todo | 남은 QC 발췌 오판 유형: 같은 의미 다른 형태 ("undisclosed" ↔ "not disclosed"), 출처당 1,200자 예산 경쟁 ("AI Mode in Search", 10-15) |

### MEDIUM — 운영 결함 (전환 중 발견)

| Task | 상태 | 목표 |
|------|------|------|
| RERUN-GUARD-01 | todo | `rerun_pipeline_stage`가 published 보호 검사 전에 로그 삭제·run failed 처리 (작업 칩 분리됨) |
| COST-QC-01 | done (`2e7a4655`, `b7b32507`) | daily QC 사용량이 `cumulative_usage`에 합산 안 됨 → run 합계 비용 과소. 함께 발견: 대시보드가 `summary` 행까지 더해 daily 비용 2배 (30일 $17.53 → $9.78) — [[2026-10-20-cost-accounting-fix]]. 테스트 959 통과, 로컬 대시보드 확인. 배포 후 다음 run에서 `summary` ≈ 단계 합계 확인 |
| QC-EVIDENCE-04 | todo | `enriched_map`이 research/business 공용 → business frontload 발췌 후보에 research 보강 자료 혼입 |
| WEEKLY-CITE-01 | todo | W42 weekly: action 항목 저장소명 인용, 2차 보도 단정 서술, learner 약어 미설명 (sol 지적, 감점만) |
| ENV-EXAMPLE-01 | todo | 루트 CLAUDE.md가 요구하는 `.env.example` 부재 → 생성 (모델 변수는 쓰지 않음) |
| DEP-CLEAN-01 | todo | 미사용 `pydantic-ai` 의존성 제거 검토 |
| PERSONA-PARALLEL-01 | todo (10-26 이후) | 카테고리 안 expert/learner/beginner 작성 순차 → 병렬 (작성 구간 ~1/3, 10-15 research learner 490s). flex 동시 6건 거절률 측정 필요 |
| QUIZ-PARTIAL-01 | done (`e0086ab0`) | 퀴즈 일부 누락(10-18 business KO expert, 5/6) 발행 시 어드민 health 카드에 "부분 누락" 표시 — [[2026-10-20-quiz-partial-health]]. 테스트 11/11, build 통과, 로컬 어드민 375px·1280px 확인 |
| RECOVERY-STALE-01 | todo | 09:00 write 복구의 75분 stale 판정: 원래 run이 아직 작성 중이면 중복 작성 가능 (기존 동작) |

### 뉴스 파이프라인 rolling 백로그 (HB-QM에서 이관)

| Task | 상태 | 목표 |
|------|------|------|
| NQ-09 | todo | 랭킹에 "어제 발행 뉴스 제목" 전달 — 같은 이벤트 반복 방지 |
| NQ-15 | todo | Learner 콘텐츠 재설계 — 학습자 관점 재구성 |
| NQ-21 | todo | GitHub Trending 축소 + 급부상 오픈소스 별도 제공 |
| NQ-24 | todo | 파이프라인 테스트 전면 재작성 (계약 기반 mock) |
| NQ-36 | todo | CLASSIFY 프롬프트 토큰 축약 |
| NQ-43 | todo | Source confidence classifier 개선 (`confidence='low'` ~40% 오탐, 2026-04-27 감사) |

---

## 보류 백로그 (2026-10-19 이관, 재개 시 꺼내 쓰기)

> 상세 설계·근거는 원본 보드 [[ACTIVE_SPRINT-HB-QM-2026-10-19]]에 그대로 보존.

### 핸드북 (2026-05-24 이후 파이프라인 정지)
- **이관 게이트였던 것:** HB-MIGRATE-138 (138개 v4 재생성), HB-SEED-800 ([[2026-04-19-handbook-seed-800]], 800개 ~$400~800 추정), HQ-01 (hallucination 수정), HQ-02 (비기술 용어 archive), HQ-11 (SEO JSON-LD — 미구현 확인)
- HB-SEED-01/02/10/12/20~25/30/31/40~42/50, HB-SEED-PROMPT-01 ([[2026-05-12-handbook-category-prompt-architecture]])
- HB-MEASURE-02~04 (02는 4/16 "doing" 이후 커밋 0), HQ-03/06/07/08/12/13, HB-QUALITY-01~04, HB-UX-06
- 재개 시 주의: 2026-10-19 기준 handbook writer도 gpt-6.1-sol (main 역할 공유). advisor는 reasoning 역할 공유 (분리 재검토 시점 = HB-SEED-800 재개)

### 유령·선택 과제
- README-01, UA-02~07 (분석 차트), WEBHOOK-USER-01a~e (`00044_user_webhooks.sql`만 존재)
- COMMUNITY-01, HANDBOOK-LEVEL-LINK-01, QUALITY-HYBRID-01, PERF-TERMS-CACHE-01

---

## 이전 스프린트 체인

- **NP-GPT6** (2026-10-13 ~) — **현재**
- [[2026-10-19-hbqm-sprint-close|HB-QM]] (2026-04-10 ~ 2026-10-19) — 보류 종료 (게이트 미통과, 핸드북 정지). mid-sprint ship: NP-HARDEN, v11, GPT-5, beginner 페르소나
- [[2026-04-10-np4q-sprint-close|NP4-Q]] (2026-03-15 ~ 2026-04-10) — 게이트 전부 통과
- Phase 3B-SHARE (2026-03-08 ~ 2026-03-13), Phase 3A-SEC (2026-03-08 ~ 2026-03-09)

## Related

- [[2026-10-13-news-pipeline-gpt6-upgrade]] — GPT-6 전환 단일 기록
- [[2026-10-15-news-prompt-revision]] — 프롬프트 개정 + A/B
- [[2026-10-15-frontload-claim-grounding]] — frontload 주장 검증 설계
- [[Phase-Flow]], [[Implementation-Plan]], [[Checklists-&-DoD]]
