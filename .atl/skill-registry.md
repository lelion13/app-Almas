# Skill Registry — app-Almas

Generated for SDD. Project skills and conventions agents should load.

## Project conventions
- `AGENTS.md` — stack baseline, security (JWT/bcrypt), layout
- `.cursor/rules/core-stack-standards.mdc`
- `.cursor/rules/backend-fastapi-pydantic.mdc`
- `.cursor/rules/security-auth-jwt-bcrypt.mdc`
- `openspec/config.yaml` — SDD context and phase rules
- `openspec/specs/*/spec.md` — product source of truth
- `docs/monthly-closings-spec.md` — detailed Excel/cierres notes (supplement)
- `docs/vps-deploy.md` — production deploy + DB dump/restore

## Useful user skills (by trigger)
| Skill | When |
|-------|------|
| `sdd-*` | Spec-driven change lifecycle |
| `dockerSeguridadHostinger` | Audit/harden VPS Docker/Traefik/GHCR |
| `api-design-principles` | New/changed API endpoints |
| `frontend-design` | New UI surfaces (prefer existing Almas patterns) |

## Persistence
- OpenSpec filesystem: `openspec/`
- Engram topic: `sdd-init/app-Almas`
