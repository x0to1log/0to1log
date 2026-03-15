---
title: Backup & Recovery Playbook
tags:
  - operations
  - backup
  - recovery
  - playbook
source: docs/05_Infrastructure.md
---

# Backup & Recovery Playbook

데이터 백업 전략과 장애 복구 절차. Supabase DB 백업, 소스 코드 보호, 장애 시나리오별 복구 단계를 정리한다.

---

## Supabase Backup

| 항목 | 설정 |
|---|---|
| **자동 백업** | Free 티어: 일일 자동 백업 (7일 보관) |
| **Point-in-Time Recovery** | Pro 플랜 이상에서 사용 가능 (현재 불가) |
| **수동 백업** | Dashboard > Database > Backups에서 수동 다운로드 |

> [!warning] Free 티어 백업 제한
> Free 티어의 자동 백업은 7일만 보관되며, Point-in-Time Recovery를 지원하지 않는다. 스키마 변경 전이나 중요 마일스톤 직후에는 반드시 수동 백업을 수행할 것.

---

## Manual Backup Procedure

### 1. `pg_dump` 실행

```bash
pg_dump --format=custom --file=backup_$(date +%Y%m%d).dump "$DATABASE_URL"
```

### 2. 저장 위치

- 로컬 머신 + 클라우드 스토리지(Google Drive 등)에 이중 보관
- `.dump` 파일은 Git에 포함하지 않는다

### 3. 백업 주기

| 시점 | 이유 |
|---|---|
| Phase 완료 시 | 스키마 + 데이터 스냅샷 |
| 파이프라인 첫 실행 성공 후 | AI 생성 데이터 첫 백업 |
| 스키마 변경 전 | 마이그레이션 실패 시 롤백용 |
| 월 1회 | 정기 백업 습관 |

### 4. 검증

- 복원 테스트: 별도 DB에 `pg_restore`로 덤프를 복원해 데이터 무결성 확인
- 주요 테이블 row count 비교

> [!note] 소스 코드 백업
> GitHub이 곧 코드 백업이다. 단, 환경 변수와 시크릿은 Git에 없으므로 `.env.example`에 키 이름을 보관하고 실제 값은 비밀번호 관리자(1Password/Bitwarden)에 저장한다.

---

## Disaster Recovery

| Scenario | Impact | Recovery Steps | RTO |
|---|---|---|---|
| **DB 데이터 손실** | 서비스 데이터 유실 | Supabase 자동 백업에서 복원 (7일 이내) | 30분 |
| **DB 손상 (스키마 변경 실패)** | 서비스 중단 | 수동 백업 `pg_restore` → 마이그레이션 재시도 | 30분~1시간 |
| **Vercel 빌드 실패** | 프론트엔드 배포 중단 | 이전 커밋으로 `git revert` → 자동 재배포 | 5분 |
| **Railway 크래시** | 백엔드 API 중단 | 자동 재시작 대기. 지속 시 이전 배포로 rollback (Railway UI) | 1~5분 |
| **Supabase 장애** | 전체 서비스 중단 | Supabase 인프라 복구 대기 (통제 불가). Status 페이지 확인 | 10분~수 시간 |
| **AI 파이프라인 실패** | 뉴스 큐레이션 중단 | `admin_notifications` 확인 → 원인 파악 → 수동 재실행 | 5~10분 |
| **환경 변수 유실** | 서비스 인증 실패 | `.env.example` + 비밀번호 관리자에서 복원 → 플랫폼 재설정 | 10분 |
| **도메인 만료** | 사이트 접근 불가 | Cloudflare에서 갱신. Vercel 연결은 자동 유지 | 24시간 |

> [!important] 장애 발생 시
> 1. Supabase / Vercel / Railway 각 서비스의 Status 페이지를 먼저 확인한다.
> 2. 인프라 문제가 아니면 최근 배포 이력을 점검한다.
> 3. 복구 후 root cause를 기록한다.

---

## Rollback Procedure

### Code Rollback

- **Vercel**: `git revert <commit>` 후 push → 자동 재배포
- **Railway**: Railway UI에서 이전 배포 선택 → rollback, 또는 `git revert` 후 push

### Database Rollback

- 마이그레이션 실패 시: 변경 전 수동 백업에서 `pg_restore`
- Supabase 자동 백업: Dashboard > Database > Backups에서 복원 (7일 이내)
- 마이그레이션 스크립트에 `DOWN` 로직이 있다면 역순 실행

### Pipeline Failure Recovery

- 동일한 `batch_id`로 파이프라인 재실행
- `admin_notifications` 테이블에서 실패 원인 확인
- 부분 실패 시 resume 로직 활용 (artifacts 기반 이어하기)

---

## Related
- [[Infrastructure-Topology]] — 백업 대상 인프라
- [[Security]] — 보안과 연결된 복구 전략
