# 프롬프트 엔지니어링 검수 체크리스트

> 검수 기준: prompt-engineering-patterns 스킬
> 검수일: 2026-03-16

---

## 검수 대상 프롬프트 (7개)

### 1. RANKING_SYSTEM_PROMPT ✅ 양호
- [x] 역할 명확 (AI news editor)
- [x] JSON 출력 포맷 명시
- [x] 규칙 간결 (4개)
- [ ] v3에서 CLASSIFICATION으로 대체됨 — 레거시로 유지 중

### 2. CLASSIFICATION_SYSTEM_PROMPT ✅ 양호
- [x] 카테고리 + 서브카테고리 명확
- [x] 규칙 6개 — 적절
- [x] 같은 기사 양쪽 허용 (규칙 2)
- [ ] ~~Few-shot 예시 없음~~ → 분류는 zero-shot으로 충분

### 3. FACT_EXTRACTION_SYSTEM_PROMPT ⚠️ 개선 필요
- [x] JSON 스키마 상세
- [x] 신뢰도 기준 (high/medium/low) 명시
- [ ] **headline_ko 규칙 번호 오류** (5 다음에 7) → 수정 필요
- [ ] **시간 제약 없음** — "오늘의 뉴스만" 지시 없음

### 4. GENERATE_BASIC_PROMPT ⚠️ 개선 완료 (v2)
- [x] Section-per-key JSON 출력 (생략 방지)
- [x] 핸드북 링크 제거 (코드 후처리)
- [x] DOMAIN CONTEXT 포함
- [ ] **Few-shot 예시 없음** → P0 개선 (좋은 출력물 확보 후)
- [ ] **DOMAIN CONTEXT 중복** (Advanced와 동일) → 간소화 가능

### 5. GENERATE_ADVANCED_PROMPT ⚠️ 개선 필요
- [x] Section-per-key JSON 출력
- [x] 핸드북 링크 제거
- [ ] **DOMAIN CONTEXT 중복** → Call 1의 definition을 이미 받으므로 간소화
- [ ] **Few-shot 예시 없음** → 코드 예시 섹션이 특히 예시가 필요

### 6. EXTRACT_TERMS_PROMPT ⚠️ 개선 필요
- [x] Self-check 예시 있음
- [x] VALID_CATEGORIES + 도메인 제한
- [ ] **category 필드 output에 포함 확인** → 코드의 VALID_CATEGORIES 검증과 연동
- [ ] **3단어 초과 skip 규칙** 프롬프트에도 명시하면 더 효과적

### 7. Digest Prompts (get_digest_prompt) ⚠️ 개선 필요
- [x] Research vs Business 분리
- [x] 3 페르소나별 깊이 차이
- [ ] **시간 제약 없음** — "이 뉴스들은 오늘 수집된 것" 명시 필요
- [ ] **Graceful degradation 없음** — 출력 잘리면 중요 섹션부터 채우라는 지시 없음
- [ ] **Beginner에서 용어 유지 + 핸드북 링크** — 코드 후처리로 이동했으므로 OK

---

## 즉시 수정 항목

### P0: 지금 수정
- [ ] FACT_EXTRACTION: 규칙 번호 오류 (5→7 건너뜀) 수정
- [ ] GENERATE_ADVANCED: DOMAIN CONTEXT 간소화 (중복 제거)
- [ ] Digest prompts: "These news items were collected today" 시간 맥락 추가
- [ ] EXTRACT_TERMS: "Do not extract terms with more than 3 words" 규칙 추가
- [ ] Digest prompts: graceful degradation 지시 추가

### P1: 좋은 출력물 확보 후
- [ ] GENERATE_BASIC에 few-shot 예시 1개 추가
- [ ] GENERATE_ADVANCED 코드 섹션에 few-shot 예시 1개 추가

---

## Related
- [[Handbook-Prompt-Redesign]]
- [[2026-03-16-handbook-quality-fix-design]]
- [[2026-03-16-prompt-architecture-v2-impl]]
