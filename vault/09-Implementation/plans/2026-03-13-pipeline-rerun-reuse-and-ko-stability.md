# Pipeline Rerun Reuse and KO Stability

## Goal
- Reuse saved pipeline artifacts and ranked candidate snapshots when rerunning the same batch.
- Reduce wasted spend by skipping repeat collect/rank and resuming EN or KO generation from saved state.
- Expose rerun mode and reuse context clearly in admin.

## Scope
- `run_daily_pipeline(batch_id, mode="resume")`
- `resume` mode reuses `news_candidates` snapshot when ranking metadata exists.
- `force_refresh` mode recollects and reranks.
- Reuse saved EN drafts when KO is missing.
- Extend `pipeline_artifacts` to store KO partial artifacts for `research` and `business`.
- Resume KO translation from saved sections or fields.
- Add admin `Force Refresh` button and show reuse metadata in `Pipeline Runs`.

## Resume Rules
- `resume` first checks whether the batch already has ranked `news_candidates`.
- If ranked candidates exist, rebuild `research_pick`, `business_main_pick`, and `related_picks` from the snapshot.
- Novelty gate still runs on rerun.
- If saved `research/en` exists and `research/ko` is missing, only rerun KO translation.
- If saved `business/en` exists and `business/ko` is missing, only rerun KO translation.
- If complete EN draft is missing, use `pipeline_artifacts` to resume partial EN or KO work.

## KO Partial Artifacts
- `research/ko` artifacts store translated markdown sections keyed by `source_post_id`.
- `business/ko` artifacts store translated fields keyed by `source_post_id`.
- Resume only missing sections or fields on rerun.
- If a KO field fails validation, persist completed translated content before stopping.

## Admin UX
- Dashboard keeps `Run Pipeline` as default `resume`.
- Add `Force Refresh` for full recollect/rerank.
- `Pipeline Runs` detail shows:
  - run mode
  - reused candidates/ranking
  - resumed from saved EN
  - resumed from partial artifact
  - locale-specific partial artifacts

## Notes
- Partial artifacts are internal recovery data, not public drafts.
- Public rendering continues to read only from `news_posts`.
