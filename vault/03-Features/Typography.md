# Typography

> 폰트 시스템. 대상 파일: `frontend/src/styles/global.css`, `frontend/src/components/Head.astro`

## 변경 전 (원본)

| 역할 | 영문 | 한국어 | 비고 |
|------|------|--------|------|
| 마스트헤드 | Playfair Display | Noto Serif KR | |
| 헤딩 | Playfair Display | Noto Serif KR | |
| 본문/UI | Lora | Noto Serif KR | 전체 세리프 |
| 블로그 마스트헤드 | Gowun Batang | Gowun Batang | 블로그 전용 |
| 블로그 본문/UI | IBM Plex Sans | IBM Plex Sans KR | 블로그만 산세리프 |
| 코드 | JetBrains Mono | D2Coding | |

## 변경 후 (현재 적용 중)

| 역할 | 영문 | 한국어 | 비고 |
|------|------|--------|------|
| **로고 (0to1log)** | Playfair Display | - | 고정, 변경 불가 |
| 마스트헤드 | Space Grotesk | NanumSquareExtraBold | |
| 헤딩 | Space Grotesk | NanumSquare | |
| 본문/UI | Jost | NanumSquare | |
| 블로그 전체 | 위와 동일 | 위와 동일 | 통일 (별도 로드 제거) |
| 코드 | JetBrains Mono | JetBrains Mono | |

### 로딩 방식
- 영문: Google Fonts (`<link>`)
- 한국어: 네이버 CDN (`hangeul.pstatic.net/hangeul_static/css/nanum-square.css`)
- CSP: `style-src`, `font-src` 에 `hangeul.pstatic.net` 허용

## 테스트한 후보 폰트들

### 영문 본문/UI

| 폰트 | 분류 | 느낌 | 결과 |
|------|------|------|------|
| Lora | 세리프 | 클래식, 올드 | 원본. 무겁고 올드한 느낌 |
| Inter | 산세리프 | 깔끔, 모던, 무난 | 테스트함. 너무 무난 |
| DM Sans | 산세리프 | 테크/AI, 모던 | 테스트함 |
| **Jost** | 산세리프 | 기하학적, 세련 | **채택** |

### 영문 헤딩

| 폰트 | 분류 | 느낌 | 결과 |
|------|------|------|------|
| Playfair Display | 세리프 | 뉴스, 클래식, 무게감 | 원본. 로고 전용으로 유지 |
| Newsreader | 세리프 | 에디토리얼, 신뢰감 | 테스트함 |
| **Space Grotesk** | 산세리프 | 테크, 독특한 캐릭터 | **채택** |

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
| **NanumSquare** | 산세리프 | 깔끔, 균형 | **채택** |

## font-experiments 브랜치

로컬 브랜치 `font-experiments`에 테스트 커밋 보존:

| 커밋 | 내용 |
|------|------|
| `a00fffa` | NanumSquare 한국어 |
| `9596669` | NanumSquareRound 한국어 |
| `ee6906d` | Space Grotesk + Jost + NanumSquare (현재 main과 동일) |

## 디자인 결정 근거

- **세리프 → 산세리프**: 원본이 전체 세리프라 무겁고 올드한 느낌. AI/테크 뉴스 사이트에 맞게 모던한 산세리프로 전환
- **블로그 폰트 통일**: IBM Plex Sans 별도 로드 제거 → Google Fonts 요청 1회로 통합, 사이트 전체 일관성 확보
- **로고 Playfair Display 고정**: 브랜드 아이덴티티 유지. `.site-brand-link`, `.admin-sidebar-logo`에 직접 지정
- **한국어 NanumSquare**: 깔끔하고 균형 잡힌 산세리프. 네이버 CDN으로 안정적 로드
