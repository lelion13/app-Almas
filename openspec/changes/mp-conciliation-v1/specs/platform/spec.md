# Delta for Platform

## MODIFIED Requirements

### Requirement: Product scope (current)

In scope: monthly closings, SigueFit income imports, expense Excel imports, manual expenses, teachers catalog, JWT auth, VPS deploy, **and admin Conciliación Mercado Pago V1** (OAuth multi-account connect + on-demand payment income display without persistence or SigueFit matching).

Behavioral source of truth for MP V1: `openspec/specs/mercado-pago/spec.md` (after archive) / change delta `openspec/changes/mp-conciliation-v1/specs/mercado-pago/spec.md`.

Explicitly out of product scope today:
- Mercado Pago ↔ SigueFit reconciliation / auto-match / webhooks / egresos (deferred beyond V1)
- Self-service password reset UI
- Public user registration API
- Refresh tokens for Almas JWT sessions

(Previously: listed “Mercado Pago reconciliation / auto-match” as entirely out of scope with no Conciliación module.)

#### Scenario: Conciliación is in product scope for admin
- **GIVEN** the platform product scope after this change
- **WHEN** an admin uses Conciliación
- **THEN** OAuth account linking and on-demand income fetch MUST be considered in-scope behavior

### Requirement: Spec-driven changes

Behavioral changes SHOULD go through OpenSpec (`openspec/changes/{name}/`) and merge into `openspec/specs/{domain}/spec.md` on archive. Domains:
- `auth`
- `monthly-closings`
- `siguefit-imports`
- `expense-imports`
- `manual-expenses`
- `teachers`
- `deployment`
- `platform`
- `mercado-pago`

(Previously: domain list without `mercado-pago`.)

#### Scenario: New domain registered
- **GIVEN** a change touching Mercado Pago Conciliación
- **WHEN** specs are written
- **THEN** they MUST target the `mercado-pago` domain
