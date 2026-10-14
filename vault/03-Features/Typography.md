# Typography

> 폰트 시스템. 대상 파일: `frontend/src/styles/global.css`, `frontend/src/components/Head.astro`

## 현재 적용 중 (Soft Newsprint)

| 역할 | 폰트 | 토큰 | 비고 |
|------|------|------|------|
| 마스트헤드 / 로고 (0to1log) | Newsreader 500 | `--font-masthead` | 숫자는 lining-nums |
| 헤딩 / 디스플레이 | Hahmlet 400/600/700 | `--font-heading`, `--font-display`, `--font-article-heading`, `--font-blog-heading`, `--font-blog-masthead` | |
| 본문 / UI / 데크 | Pretendard 400-800 | `--font-body`, `--font-sans`, `--font-ui`, `--font-article-deck`, `--font-blog-body`, `--font-blog-ui` | 블로그도 동일 |
| 코드 | JetBrains Mono (D2Coding 폴백) | `--font-code` | |

- 영문·한글 모두 위 폰트로 처리 (Pretendard/Hahmlet가 한글 포함). Lora, Playfair Display, Gowun, Space Grotesk, Jost, NanumSquare는 사용하지 않는다.
- 한글에는 이탤릭을 쓰지 않는다 (이탤릭 face 없음, faux italic 금지).
- 헤딩은 `word-break: keep-all` + `text-wrap: balance`로 한글 단어가 중간에서 끊기지 않게 한다.
- 드롭캡, 3px 이중 룰(현재 1px solid), 페이지 노이즈 질감, 대문자 스몰캡 kicker는 제거됨.

## 테스트한 후보 폰트들 (과거 기록)

### 영문 본문/UI

| 폰트 | 분류 | 느낌 | 결과 |
|------|------|------|------|
| Lora | 세리프 | 클래식, 올드 | 원본. 무겁고 올드한 느낌 |
| Inter | 산세리프 | 깔끔, 모던, 무난 | 테스트함. 너무 무난 |
| DM Sans | 산세리프 | 테크/AI, 모던 | 테스트함 |
| **Jost** | 산세리프 | 기하학적, 세련 | 구 채택 (현재 미사용) |

### 영문 헤딩

| 폰트 | 분류 | 느낌 | 결과 |
|------|------|------|------|
| Playfair Display | 세리프 | 뉴스, 클래식, 무게감 | 원본. 현재 미사용 |
| Newsreader | 세리프 | 에디토리얼, 신뢰감 | 테스트함 |
| **Space Grotesk** | 산세리프 | 테크, 독특한 캐릭터 | 구 채택 (현재 미사용) |

### 한국어

| 폰트 | 분류 | 느낌 | 결과 |
|------|------|------|------|
| Noto Serif KR | 세리프 | 격식, 가독성 낮음 | 원본 |
| Noto Sans KR | 산세리프 | 깔끔, 무난 | 테스트함 |
| Gowun Dodum | 둥근 산세리프 | 부드럽고 친근 | 테스트함 |
| Gowun Batang | 세리프 | 격식, 에디토리얼 | 테스트함 |
| RIDIBatang | 세리프 | 독서, 인쇄 느낌 | 테스트함 (`font-experiments` 브랜치) |
| Continuous | 둥근 | 독특, 부드러운 | 테스트함. 변화 체감 어려움 |
| Galmuri9 | 픽셀/도트 | 레트로, 게임 | 테스트함. CDN 로딩 이슈 |
| NanumSquareRound | 둥근 산세리프 | 친근, 부드러운 | 테스트함 (`font-experiments` 브랜치) |
| **NanumSquare** | 산세리프 | 깔끔, 균형 | 구 채택 (현재 미사용) |

## font-experiments 브랜치

로컬 브랜치 `font-experiments`에 테스트 커밋 보존:

| 커밋 | 내용 |
|------|------|
| `a00fffa` | NanumSquare 한국어 |
| `9596669` | NanumSquareRound 한국어 |
| `ee6906d` | Space Grotesk + Jost + NanumSquare (현재 main과 동일) |

## 디자인 결정 근거

- **세리프 헤딩 + 산세리프 본문**: 신문 느낌은 마스트헤드·헤딩에만 주고, 긴 글 가독성은 Pretendard가 맡는다.
- **블로그 폰트 통일**: 블로그 전용 폰트 로드 없이 사이트 전체가 같은 3종(Newsreader, Hahmlet, Pretendard)을 쓴다.
- **한글 이탤릭 금지**: 한글 이탤릭 face가 없어 합성 기울임이 깨져 보임.
