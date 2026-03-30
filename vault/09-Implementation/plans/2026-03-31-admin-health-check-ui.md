# NQ-17 Admin Health Check UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 파이프라인 health check warnings를 어드민에서 한눈에 확인할 수 있도록 목록 페이지에 warning 뱃지 + 상세 페이지에 단계별 warning 표시.

**Architecture:** 백엔드 변경 없음. pipeline_logs의 `debug_meta.warnings` 배열을 프론트에서 읽어서 표시. 목록 페이지는 전체 run의 warning 합산, 상세 페이지는 단계별 warning 인라인 표시.

**Tech Stack:** Astro v5, Supabase query, CSS (global.css)

---

### Task 1: 목록 페이지 — warning 카운트 집계 + 뱃지

**Files:**
- Modify: `frontend/src/pages/admin/pipeline-runs/index.astro`

**Step 1: pipeline_logs 쿼리에 debug_meta 추가**

현재 (line ~108):
```typescript
const { data: logs } = runIds.length
  ? await sb.from('pipeline_logs').select('run_id, pipeline_type, cost_usd, tokens_used').in('run_id', runIds)
  : { data: [] };
```

변경:
```typescript
const { data: logs } = runIds.length
  ? await sb.from('pipeline_logs').select('run_id, pipeline_type, cost_usd, tokens_used, debug_meta').in('run_id', runIds)
  : { data: [] };
```

PipelineLog 타입에 debug_meta 추가:
```typescript
type PipelineLog = {
  run_id: string;
  pipeline_type: string;
  cost_usd: number | string | null;
  tokens_used: number | null;
  debug_meta: Record<string, unknown> | null;
};
```

**Step 2: RunCard에 warningCount 추가**

```typescript
type RunCard = PipelineRun & {
  ...existing...
  warningCount: number;
};
```

**Step 3: warning 카운트 집계**

totals Map에 warningCount 추가. filteredLogs 루프에서:

```typescript
// Count warnings from debug_meta
const meta = log.debug_meta as Record<string, unknown> | null;
const warnings = (meta?.warnings ?? []) as string[];
current.warningCount = (current.warningCount ?? 0) + warnings.length;
```

runs.push에서:
```typescript
warningCount: metric?.warningCount ?? 0,
```

**Step 4: 카드 UI에 warning 뱃지 추가**

pipeline-run-card__footer 안, errorSummary/ok 뒤에:
```html
{run.warningCount > 0 && (
  <span class="pipeline-run-card__warning">⚠️ {run.warningCount} warning{run.warningCount > 1 ? 's' : ''}</span>
)}
```

**Step 5: CSS**

global.css에 추가:
```css
.pipeline-run-card__warning {
  color: var(--color-warning, #d97706);
  font-size: 0.8rem;
  font-weight: 500;
}
```

**Step 6: ruff/build check + commit**

```
feat(admin): pipeline-runs 목록에 health check warning 뱃지
```

---

### Task 2: 상세 페이지 — 단계별 warning 인라인 표시

**Files:**
- Modify: `frontend/src/pages/admin/pipeline-runs/[runId].astro`

**Step 1: warning 추출 헬퍼**

기존 `debugMetaObject()` 활용:
```typescript
function getWarnings(log: PipelineLog): string[] {
  const meta = debugMetaObject(log);
  const warnings = meta.warnings;
  return Array.isArray(warnings) ? warnings as string[] : [];
}
```

**Step 2: 단계 카드 header에 warning 뱃지**

pipeline-stage-card__identity 안, title 옆에:
```html
{getWarnings(log).length > 0 && (
  <span class="pipeline-stage-warning-badge">⚠️ {getWarnings(log).length}</span>
)}
```

**Step 3: warning 내용 표시**

pipeline-stage-card__chips 뒤, error_message 표시 전에:
```html
{getWarnings(log).length > 0 && (
  <div class="pipeline-stage-warnings">
    {getWarnings(log).map((w) => (
      <p class="pipeline-stage-warning-item">⚠️ {w}</p>
    ))}
  </div>
)}
```

**Step 4: CSS**

```css
.pipeline-stage-warning-badge {
  color: var(--color-warning, #d97706);
  font-size: 0.75rem;
  font-weight: 500;
  margin-left: 0.5rem;
}

.pipeline-stage-warnings {
  margin: 0.5rem 0;
  padding: 0.5rem 0.75rem;
  background: color-mix(in srgb, var(--color-warning, #d97706) 8%, transparent);
  border-radius: 6px;
  border-left: 3px solid var(--color-warning, #d97706);
}

.pipeline-stage-warning-item {
  font-size: 0.8rem;
  color: var(--color-warning, #d97706);
  margin: 0.25rem 0;
}
```

**Step 5: build check + commit**

```
feat(admin): pipeline-runs 상세에 단계별 health check warning 표시
```
