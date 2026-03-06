# Backend Rules

FastAPI + Railway (Nixpacks). ?ㅽ럺 ?곸꽭 ??`docs/03_Backend_AI_Spec.md`, `docs/05_Infrastructure.md`

## 援ъ“

- `main.py` ??FastAPI app + ?쇱슦???깅줉 + CORS
- `core/` ??config, database, security (?섏〈??二쇱엯)
- `routers/` ???붾뱶?ъ씤??洹몃９ (cron, admin, search, community)
- `services/` ??鍮꾩쫰?덉뒪 濡쒖쭅 (?먯씠?꾪듃, ?뚯씠?꾨씪??
- `models/` ??Pydantic ?ㅽ궎留?

## Python

- Virtualenv policy: use `backend/.venv` only (`backend/venv` is not allowed).
- 踰꾩쟾: 3.11+ (`.python-version` 李몄“)
- ?섏〈?? `requirements.txt` (Nixpacks ?먮룞 媛먯?)
- Linter: `ruff check .` (backend/ ?댁뿉???ㅽ뻾)
- Test: `pytest tests/ -v --tb=short`

## 蹂댁븞

- Admin ?붾뱶?ъ씤?? `Depends(require_admin)` ?꾩닔
- Cron ?붾뱶?ъ씤?? `x-cron-secret` ?ㅻ뜑 寃利??꾩닔
- Supabase??Service Role Key ?ъ슜 (backend ?꾩슜)
- CORS: ?덉슜 ?꾨찓?몄? ?섍꼍蹂?섎줈 愿由?(?섎뱶肄붾뵫 湲덉?)

## 諛고룷 (Railway)

- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health: `GET /health` ??`{"status": "ok"}`
- ?먮룞 諛고룷: main push
- Auto-restart on crash

## ?⑦꽩

- Fire-and-forget: Cron ??202 利됱떆 ?묐떟 + `BackgroundTasks` 鍮꾨룞湲??ㅽ뻾
- Rate limiting: `slowapi` ?곗퐫?덉씠??
- EN-KO 踰꾩쟾 ?? KO 諛쒗뻾 ??EN revision lock + version 寃利?

## 湲덉?

- `print()` ?붾쾭源?湲덉? ??`logging` 紐⑤뱢 ?ъ슜
- ?섍꼍蹂???섎뱶肄붾뵫 湲덉? ??`core/config.py` Settings ?ъ슜
- Service Role Key瑜??꾨줎?몄뿏?쒖뿉 ?몄텧?섎뒗 API ?묐떟 湲덉?
