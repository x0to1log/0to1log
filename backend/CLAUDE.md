# Backend Rules

FastAPI + Railway (Nixpacks). 스펙 상세 → `docs/03_Backend_AI_Spec.md`, `docs/05_Infrastructure.md`

## 구조

- `main.py` → FastAPI app + 라우터 등록 + CORS
- `core/` → config, database, security (의존성 주입)
- `routers/` → 엔드포인트 그룹 (cron, admin, search, community)
- `services/` → 비즈니스 로직 (에이전트, 파이프라인)
- `models/` → Pydantic 스키마

## Python

- 버전: 3.11+ (`.python-version` 참조)
- 의존성: `requirements.txt` (Nixpacks 자동 감지)
- Linter: `ruff check .` (backend/ 내에서 실행)
- Test: `pytest tests/ -v --tb=short`

## 보안

- Admin 엔드포인트: `Depends(require_admin)` 필수
- Cron 엔드포인트: `x-cron-secret` 헤더 검증 필수
- Supabase는 Service Role Key 사용 (backend 전용)
- CORS: 허용 도메인은 환경변수로 관리 (하드코딩 금지)

## 배포 (Railway)

- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health: `GET /health` → `{"status": "ok"}`
- 자동 배포: main push
- Auto-restart on crash

## 패턴

- Fire-and-forget: Cron → 202 즉시 응답 + `BackgroundTasks` 비동기 실행
- Rate limiting: `slowapi` 데코레이터
- EN-KO 버전 락: KO 발행 시 EN revision lock + version 검증

## 금지

- `print()` 디버깅 금지 → `logging` 모듈 사용
- 환경변수 하드코딩 금지 → `core/config.py` Settings 사용
- Service Role Key를 프론트엔드에 노출하는 API 응답 금지
