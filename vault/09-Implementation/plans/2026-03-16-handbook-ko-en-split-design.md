# 핸드북 KO/EN 누락 버그 — 호출 분리 설계

> 발견: 2026-03-16
> 원인: 1회 LLM 호출로 KO+EN 16개 키 동시 생성 → 토큰 소진 시 후반부 누락

---

## 문제

Basic Call에서 16개 키(8 KO + 8 EN)를 한 번에 생성.
LLM이 KO를 먼저 쓰면 EN 누락, EN을 먼저 쓰면 KO 누락.
불규칙적 — 매번 다른 언어가 빠짐.

---

## 해결 방안 3가지

### A. 3회 호출 분리 (채택)

```
Call 1: 메타 + KO Basic (term_full, korean_full, categories, definition, basic_ko_1~8)
Call 2: EN Basic (definition_en, basic_en_1~8)
Call 3: KO+EN Advanced (adv_ko_1~9, adv_en_1~9) — Advanced는 상대적으로 짧을 수 있음
```

- 장점: KO/EN 독립 → 한쪽 누락 방지. 비용 ~50% 증가 수용 가능.
- 단점: Advanced도 분리 필요할 수 있음 (모니터링 후 판단)

### B. KO/EN 교차 배치 (보류)

```json
{
  "basic_ko_1_plain": "...",
  "basic_en_1_plain": "...",
  "basic_ko_2_example": "...",
  "basic_en_2_example": "...",
  ...
}
```

- 장점: 프롬프트만 수정. 비용 변화 없음.
- 단점: 근본 해결 아님 — 여전히 후반 키 누락 가능.

### C. 언어별 완전 분리 4회 (보류)

```
Call 1: KO Basic (basic_ko_1~8)
Call 2: EN Basic (basic_en_1~8)
Call 3: KO Advanced (adv_ko_1~9)
Call 4: EN Advanced (adv_en_1~9)
```

- 장점: 가장 확실. 각 호출이 8~9키만 생성 → 토큰 충분.
- 단점: 비용 2배. 4회 호출 = 지연 시간 증가.

---

## 뉴스 다이제스트 제목 개선

현재: `"AI Research Daily — 2026-03-09"` (하드코딩)

개선: 분류된 뉴스 중 1위 기사 제목 활용
```
"GPT-5 출시와 Llama 4 오픈소스 — AI Research Daily"
```

또는 LLM 다이제스트 출력에 `headline` / `headline_ko` 키 추가.

---

## Related

- [[2026-03-16-prompt-architecture-v2-impl]]
- [[2026-03-16-handbook-quality-fix-design]]
- [[Handbook-Prompt-Redesign]]
