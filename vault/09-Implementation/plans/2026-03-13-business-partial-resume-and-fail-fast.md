# Business Partial Resume + Fail-Fast

Date: 2026-03-13
Status: implemented

## Goal
- Stop wasting tokens after `business` generation has already failed validation.
- Save reusable internal recovery artifacts so the next run can resume instead of starting over.
- Keep public publishing unchanged: only complete posts go to `news_posts`.

## Internal Contract
- New table: `pipeline_artifacts`
- Scope: internal recovery data only, never public drafts
- Match key: `batch_id + post_type + locale + candidate_url`
- Lifecycle:
  - `partial`
  - `consumed`
  - `superseded`

## Stored Payload Shape
```json
{
  "candidate": {
    "title": "string",
    "url": "string",
    "batch_id": "string"
  },
  "fact_pack": [],
  "source_cards": [],
  "analysis_data": {},
  "persona_payloads": {},
  "completed_stages": []
}
```

## Behavior
### Fail-fast
- If `content_analysis` still fails the `2000` char minimum after retries, stop immediately.
- Do not continue to persona generation after an analysis failure.
- If one persona fails after retries, stop before generating remaining personas.
- Persist the latest partial artifact before raising.

### Resume
- If `research/en` exists for the same `batch_id` and `research/ko` is missing, reuse EN and run only KO translation.
- If `business/en` exists for the same `batch_id` and `business/ko` is missing, reuse EN and run only KO translation.
- If no complete EN business draft exists, try the latest `partial` artifact for the same `batch_id + candidate_url`.
- Resume only the missing business stages.

### Admin visibility
- `Pipeline Runs` detail shows `Partial Artifacts`.
- This view is read-only in v1.
- Preview panels stay collapsed by default.

## Notes
- Partial artifacts are recovery snapshots, not publishable drafts.
- Old runs do not gain artifacts retroactively.
- New runs created after this change can resume from saved `business` partials.

## Related Plans

- [[plans/ACTIVE_SPRINT|ACTIVE SPRINT]]
