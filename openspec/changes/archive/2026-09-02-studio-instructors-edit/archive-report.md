# Archive Report: studio-instructors-edit

**Change**: studio-instructors-edit  
**Status**: ARCHIVED  
**Date**: 2026-09-02  

---

## 1. Executive Summary

The `studio-instructors-edit` change completes the SDD cycle for Estudio → Instructores:

- Junction table `studio_instructor_activities` (Alembic **013**) with catalog-only activity links.
- Full admin UI: create form, list with **Editar** / **Eliminar** (soft), edit modal with activity checkboxes.
- **Single email** for instructors (UI + API); students retain `login_email` + `password` pair.
- Data repair migration **014** aligns legacy profile emails with linked login users.
- Production issues resolved: junction flush (false 409), PATCH email omission, StudentResponse split, browser autofill guards.

Operator confirmed instructor edit works on VPS after final backend deploy.

---

## 2. Specs Synchronized to Source of Truth

| Domain Spec | Action | Key Updates |
|-------------|--------|-------------|
| `openspec/specs/studio-scheduling/spec.md` | Updated | Full `Requirement: Instructors` with email rules, junction flush, scenarios |
| `openspec/specs/deployment/spec.md` | Updated | Alembic head **014**; migrations 013–014 scenarios |
| `openspec/specs/auth/spec.md` | Updated | Split student (`login_email`) vs instructor (`email`) login create |
| `openspec/specs/studio-students/spec.md` | Updated | `StudentResponse` must not inherit instructor fields |

---

## 3. Documentation Updated

- `docs/studio-ops-lessons.md` — instructores + troubleshooting table
- `docs/runbook.md`, `docs/vps-deploy.md` — head 014
- `openspec/config.yaml` — head 014; active change cleared

---

## 4. Archive Contents

- `proposal.md` ✅
- `exploration.md` ✅
- `design.md` ✅
- `tasks.md` ✅ (18/18)
- `verify-report.md` ✅
- `specs/` (delta specs) ✅
- `state.yaml` ✅
- `archive-report.md` ✅

---

## 5. SDD Cycle Complete

Ready for next change.
