# Verify report: studio-sites-edit-maps

**Date:** 2026-08-11  
**Status:** accepted for archive

## Checklist

| Check | Result |
|-------|--------|
| Tasks complete | ✅ |
| Migration `006` | ✅ |
| Schemas + model maps_url | ✅ |
| UI create + inline PATCH | ✅ |
| Active-only pickers | ✅ |
| Unit tests maps_url / site schemas | ✅ 7 passed (`test_studio_ops.py`) |
| Lessons + runbook | ✅ |

## Residual

- Alumno still does not see/open maps_url (intentional OUT)
- Prod needs image deploy + `alembic` head `006` via entrypoint

## Decision
Archive accepted.
