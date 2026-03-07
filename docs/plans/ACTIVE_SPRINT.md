# ACTIVE SPRINT ??Phase 2C-EXP (Frontend Experience)

> **?ㅽ봽由고듃 ?쒖옉:** 2026-03-07
> **紐⑺몴:** Newsprint ?뚮쭏 ?꾩꽦 + 由ъ뒪???곸꽭 怨좊룄??+ 諛섏쓳???묎렐???깅뒫 QA
> **李몄“:** MASTER ??`docs/IMPLEMENTATION_PLAN.md` | ?ㅽ럺 ??`docs/04~06`
> **?댁쟾 ?ㅽ봽由고듃:** Phase 2B-OPS ??2026-03-07 寃뚯씠???꾩껜 ?듦낵

---

## ?ㅽ봽由고듃 ?꾨즺 寃뚯씠??

- [ ] 諛섏쓳?? mobile/tablet/desktop ?덉씠?꾩썐 ?뺤긽
- [ ] ?묎렐?? `prefers-reduced-motion`, ?ㅻ낫???ъ빱?? ?鍮?湲곗? ?듦낵
- [ ] Lighthouse: Perf/Best/SEO/Acc 媛곴컖 `>= 85`
- [ ] Core Web Vitals 紐⑺몴: `LCP < 2.8s`, `CLS < 0.1`, `INP < 250ms`
- [ ] `cd frontend && npm run build` ??0 error
- [ ] Admin Editor mock ?뚮줈??紐⑸줉 ???곸꽭 ???몄쭛/誘몃━蹂닿린 ??諛쒗뻾 CTA) ?뺤긽
- [ ] ?쒖뒪???꾩껜 `?곹깭=done` + `泥댄겕=[x]` ?쇱튂
- [ ] `Current Doing` ?щ’??鍮꾩뼱 ?덉쓬(`-`)
- [ ] ?꾨즺 ?쒖뒪?щ쭏??`利앷굅` 留곹겕 理쒖냼 1媛?議댁옱

---

## Current Doing (1媛?怨좎젙)

| Task ID | ?곹깭 | ?쒖옉 ?쒓컖 | Owner |
|---|---|---|---|
| - | - | - | - |

洹쒖튃:
- 臾몄꽌 ??`?곹깭: doing` ?쒖뒪?ш? ?덉쑝硫????쒖뿉??諛섎뱶??1媛쒕쭔 湲곗엯?쒕떎.
- 臾몄꽌 ??`?곹깭: doing` ?쒖뒪?ш? 0媛쒕㈃ ?쒕뒗 `-`瑜??좎??쒕떎.
- ?쒖뒪???곹깭 蹂寃??????쒕? 媛숈? 而ㅻ컠?먯꽌 ?④퍡 媛깆떊?쒕떎.

---

## ?곹깭 ?낅뜲?댄듃 洹쒖튃

- ?쇳빀??怨좎젙: `?곹깭(todo/doing/review/done/blocked)` + `泥댄겕([ ]/[x])`瑜??④퍡 ?ъ슜?쒕떎.
- `todo/review/doing/blocked`??`泥댄겕: [ ]`濡??좎??쒕떎.
- `done`? 諛섎뱶??`泥댄겕: [x]`濡?蹂寃쏀븳??
- `?곹깭`? `泥댄겕`媛 遺덉씪移섑븯硫?臾댄슚濡?媛꾩＜?쒕떎. ?? `?곹깭: done` + `泥댄겕: [ ]` 湲덉?.
- `利앷굅`???쒖뒪???꾨즺(`?곹깭: done`) ???꾩닔?대ŉ, PR/濡쒓렇/?ㅽ겕由곗꺑 以?理쒖냼 1媛?留곹겕瑜??④릿??

---

## ?쒖뒪??(?ㅽ뻾 ?쒖꽌)

### 1. Newsprint ?좏겙/?뚮쭏/怨듯넻 而댄룷?뚰듃 ?뺣━ `[P2C-UI-11]`
- **泥댄겕:** [x]
- **?곹깭:** done
- **紐⑹쟻:** 湲곗〈 newsprint 而댄룷?뚰듃(Shell, ListCard, SideRail, CategoryFilter, ArticleLayout) ?뺣━ + ?뚮쭏 ?좏겙 ?듯빀 (dark/light/pink)
- **?곗텧臾?** `frontend/src/components/newsprint/` ?뺣━ + `frontend/src/styles/global.css` ?좏겙 泥닿퀎??
- **?꾨즺 湲곗?:** `npm run build` 0 error + 3 ?뚮쭏 preview ?섏씠吏 ?뺤긽 ?뚮뜑留?
- **寃利?** `cd frontend && npm run build` + preview ?섏씠吏 ?섎룞 ?뺤씤
- **利앷굅:** commits f3c39c5..dc3ced5 (6 commits: 而댄룷?뚰듃 5媛?+ CSS ?좏겙 3?뚮쭏 + preview 3?섏씠吏 + 釉뚮옖??援먯껜)
- **李몄“:** IMPLEMENTATION_PLAN 짠3 2C-EXP
- **?섏〈??** ?놁쓬

### 2. /en|ko/log 由ъ뒪???곸꽭 + ?ㅺ뎅???ㅼ쐞泥?+ ?붾㈃ ?곹깭 `[P2C-UI-12]`
- **泥댄겕:** [x]
- **?곹깭:** done
- **紐⑹쟻:** 由ъ뒪???곸꽭 ?섏씠吏??newsprint ?ㅽ???蹂멸꺽 ?곸슜 + ?ㅺ뎅???ㅼ쐞泥?+ empty/error/loading ?곹깭 泥섎━
- **?곗텧臾?** `frontend/src/pages/en|ko/log/` ?섏씠吏 ?낅뜲?댄듃 + `NewsprintNotice` 而댄룷?뚰듃
- **?꾨즺 湲곗?:** EN/KO 由ъ뒪???곸꽭 ?뺤긽 ?뚮뜑留?+ ?몄뼱 ?꾪솚 ?숈옉 + 鍮??곹깭 ?쒖떆
- **寃利?** `npm run build` 0 error ??
- **利앷굅:** ?대쾲 而ㅻ컠 (i18n ??3媛?+ NewsprintNotice 而댄룷?뚰듃 + 由ъ뒪???곸꽭 ?먮윭 泥섎━ + 404 UI)
- **鍮꾧퀬:** Loading state??SSR 援ъ“???대떦 ?놁쓬 (?쒕쾭媛 ?꾩꽦??HTML ?꾩넚). 誘몄뿰寃?env 誘몄꽕????empty, 荑쇰━ ?ㅽ뙣 ??error濡?援щ텇.
- **李몄“:** IMPLEMENTATION_PLAN 짠3 2C-EXP
- **?섏〈??** P2C-UI-11

### 3. ?몃꽕???대?吏 newsprint ?꾪꽣 `[P2C-UI-13]`
- **泥댄겕:** [x]
- **?곹깭:** done
- **紐⑹쟻:** Featured 移대뱶??og_image_url 湲곕컲 ?몃꽕???뚮뜑留?+ 湲곗〈 .img-newsprint ?꾪꽣 ?곌껐
- **?곗텧臾?** `global.css` grid ?덉씠?꾩썐 + EN/KO 由ъ뒪??featured 移대뱶 ?대?吏 + preview 3?섏씠吏 mock ?대?吏
- **?꾨즺 湲곗?:** ?대?吏 湲곕낯 ?묐갚+?명뵾??+ hover ??而щ윭 蹂듭썝 transition ?숈옉
- **寃利?** `npm run build` 0 error ??+ preview ?섏씠吏 ?쒓컖 ?뺤씤
- **利앷굅:** commits 2f1316c..920102b (CSS grid + EN/KO featured thumbnail + preview mock images)
- **鍮꾧퀬:** ?섎㉧吏 移대뱶???띿뒪???꾩슜 ?좎?. ?곸꽭 ?섏씠吏 hero ?대?吏??蹂꾨룄 ?쒖뒪?щ줈 遺꾨━.
- **李몄“:** IMPLEMENTATION_PLAN 짠3 2C-EXP
- **?섏〈??** P2C-UI-12

### 4. Admin Editor ?붾㈃(留덊겕?ㅼ슫 ?묒꽦/誘몃━蹂닿린) `[P2C-UI-14]`
- **泥댄겕:** [x]
- **?곹깭:** done
- **紐⑹쟻:** `/admin`?먯꽌 ?쒕옒?꾪듃 ?몄쭛 ?붾㈃(留덊겕?ㅼ슫 ?묒꽦 + 誘몃━蹂닿린 + Save/Publish ?≪뀡)??newsprint ?ㅼ쑝濡?援ы쁽
- **?곗텧臾?** Admin Editor UI 而댄룷?뚰듃/?섏씠吏 ?낅뜲?댄듃
- **?꾨즺 湲곗?:** ?몄쭛 ?낅젰, 誘몃━蹂닿린 ?꾪솚, Save/Publish CTA ?몄텧 諛?湲곕낯 ?숈옉(mock) ?뺤씤
- **寃利?** `cd frontend && npm run build` 0 error ??
- **利앷굅:** commits d2015c8..529886c (milkdown install + admin CSS + dashboard + editor page)
- **李몄“:** IMPLEMENTATION_PLAN 짠3 2C-EXP, 04_Frontend_Spec 짠3-5
- **?섏〈??** P2C-UI-13

### 5. Admin Editor ?곹깭/沅뚰븳/?먮윭 泥섎━(mock) `[P2C-UI-15]`
- **泥댄겕:** [x]
- **?곹깭:** done
- **紐⑹쟻:** Admin Editor??loading/empty/404/401/403 ?곹깭? ???諛쒗뻾 ?쇰뱶諛깆쓣 OpenAPI 怨좎젙 ?ㅽ궎留?湲곕컲 mock?쇰줈 援ы쁽
- **?곗텧臾?** ?곹깭蹂?UI, ?ㅻ쪟 硫붿떆吏, ?≪뀡 ?쇰뱶諛?泥섎━
- **?꾨즺 湲곗?:** 沅뚰븳/?먮윭 ?곹깭蹂??붾㈃怨?硫붿떆吏媛 ?쇨??섍쾶 ?몄텧?섍퀬, ?몄쭛 ?뚮줈?곌? 以묐떒 ?놁씠 蹂듦뎄 媛??
- **寃利?** `cd frontend && npm run build` + ?곹깭蹂??섎룞 ?쒕굹由ъ삤 ?먭?
- **利앷굅:** commits 9e39904..ab58654 (unauthorized variant + feedback CSS + list state branching + editor state/feedback/save)
- **李몄“:** IMPLEMENTATION_PLAN 짠1 Hard Gate, 짠3 2C-EXP
- **?섏〈??** P2C-UI-14

### 6. 諛섏쓳???묎렐???깅뒫 QA `[P2C-QA-11]`
- **泥댄겕:** [ ]
- **?곹깭:** todo
- **紐⑹쟻:** Lighthouse 痢≪젙 + Core Web Vitals + ?묎렐???먭?
- **?곗텧臾?** Lighthouse 由ы룷??(Perf/Best/SEO/Acc >= 85) + ?묎렐???먭? 寃곌낵
- **?꾨즺 湲곗?:** Lighthouse 4媛???ぉ 紐⑤몢 >= 85, CWV 紐⑺몴 異⑹”, ?묎렐??湲곕낯 ?듦낵
- **寃利?** Lighthouse CLI ?먮뒗 DevTools 痢≪젙 寃곌낵 罹≪쿂
- **利앷굅:** -
- **李몄“:** IMPLEMENTATION_PLAN 짠3 2C Gate
- **?섏〈??** P2C-UI-15

---

## ?섏〈???먮쫫

```
P2C-UI-11 ??P2C-UI-12 ??P2C-UI-13 ??P2C-UI-14 ??P2C-UI-15 ??P2C-QA-11
```

---

## ?댁쟾 ?ㅽ봽由고듃 ?붿빟 (Phase 2B-OPS)

> Phase 2B-OPS (2026-03-07) ??寃뚯씠???꾩껜 ?듦낵, 4媛??쒖뒪???꾨즺, 49 tests passed.
> - OpenAPI ?ㅽ궎留?怨좎젙 (12 schemas, 6 endpoints)
> - AI Agent 3醫?援ы쁽 (Ranking gpt-4o-mini, Research/Business gpt-4o)
> - Admin CRUD ?ㅺ뎄??(list/get/publish/update + 401/403 遺꾨━)
> - Cron skeleton (secret 寃利?+ 202 諛섑솚)

---

## ?댁쟾 ?ㅽ봽由고듃 ?붿빟 (Phase 2A)

> Phase 2A (2026-03-06 ~ 03-07) ??寃뚯씠???꾩껜 ?듦낵, 6媛??쒖뒪???꾨즺.
> - DB 留덉씠洹몃젅?댁뀡 (`supabase/migrations/00002_pipeline_tables.sql`, 5媛??뚯씠釉?+ RLS)
> - Pydantic ?ㅽ궎留??뺤쓽 (ranking, research, business, common)
> - ?댁뒪 ?섏쭛 ?쒕퉬??Mock ?뚯뒪???꾨즺 (Tavily/HN/GitHub + dedup)
> - ?뚯씠?꾨씪??Lock/Stale Recovery 援ы쁽 諛??뚯뒪??(8 passed)
> - Security 誘몃뱾?⑥뼱 + Vercel Cron Trigger skeleton ?꾨즺

---

## ?ㅼ쓬 ?ㅽ봽由고듃 ?덇퀬

Phase 2C 寃뚯씠???듦낵 ????**Phase 2D-INT** (?듯빀/E2E: Mock ?쒓굅 + ?짞PI ?곕룞 + E2E ?뚯뒪??

---

## Rail Copy Note

- List rail copy set approved: 오늘의 편집 노트 / Editor's Note, 지금 많이 읽는 글 / Most Read, 처음 읽는 분께 / Start Here
- Most Read is currently fed by a latest-published fallback until analytics-based popularity data exists.
- Article detail rail remains a separate follow-up and should not reuse the list-rail headings.
## 2C-EXP Addendum (Stitch Compatibility)

- [x] `2C-UI-01` Prototype compatibility cleanup completed
  Evidence: `frontend/example_dark.html`, `frontend/example_light.html`, `frontend/example_list.html`
- [x] `2C-UI-02` `/en|ko/log` list/detail style migration completed
  Evidence: `frontend/src/pages/en/log/index.astro`, `frontend/src/pages/ko/log/index.astro`, `frontend/src/pages/en/log/[slug].astro`, `frontend/src/pages/ko/log/[slug].astro`
- [x] `2C-QA-01` Preview routes added for visual validation
  Evidence: `frontend/src/pages/preview/newsprint-dark.astro`, `frontend/src/pages/preview/newsprint-light.astro`

