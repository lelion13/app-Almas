# Verify report: studio-ops-mvp

**Date:** 2026-08-10  
**Status:** accepted for archive (applied in repo; deploy ops documented)

## Checklist

| Check | Result |
|-------|--------|
| Tasks Phase 1–6 marked complete | ✅ `tasks.md` |
| Backend router + service + migration `005` | ✅ |
| Frontend admin / instructor / alumno portals | ✅ |
| Unit tests credit/overlap/scope | ✅ `pytest tests/test_studio_ops.py` (3 passed at implement) |
| Docs runbook + lessons | ✅ `docs/runbook.md`, `docs/studio-ops-lessons.md` |
| Main specs merged | ✅ `studio-*`, auth, platform, deployment |
| Critical open bugs during pilot | 🔧 rooms catalog UI fixed (`4488fb1`) |
| Full API 403 matrix automated | ⚠️ partial (unit service rules; matrix not exhaustive e2e) |
| Prod always pulled after every image | ⚠️ operator-dependent (`pull` required; Hostinger update insufficient alone) |

## Known residual risks

- Attendance credit policy is “consume at book”; settings `no_show_deducts_credit` not fully driving second deduction.
- Instructor cannot mass-cancel via dedicated HTTP (admin only).
- No e2e browser tests for portals.
- `:main` deploy requires explicit pull on VPS.

## Decision

Accept archive: product behavior is coded, documented in main specs + lessons; residuals are documented non-blockers.
