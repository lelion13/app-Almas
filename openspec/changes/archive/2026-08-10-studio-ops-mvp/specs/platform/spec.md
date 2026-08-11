# Delta: Platform — studio ops MVP

## MODIFIED Requirements

### Requirement: Product scope (current)

In scope remains existing Almas domains **plus** studio operations MVP: multi-sede rooms/activities, students, bookings, packs, instructor/alumno portals — **coexisting** with SigueFit/closings/MP Conciliación.

Explicitly out (unchanged + studio deferrals): SigueFit replacement; closings fed from studio; recepción role; auto notifications; check-in; timed reschedule caps; plan freeze; mensual libre; rich studio reports; MP pack checkout; AFIP; Google Calendar; Teachers↔Instructor link.

#### Scenario: Studio coexists
- **GIVEN** the platform after this change
- **WHEN** admin uses Conciliación or cierres
- **THEN** those flows MUST continue to work independently of studio modules

### Requirement: Spec-driven changes

Domains list MUST include:
- `studio-sites`
- `studio-scheduling`
- `studio-students`
- `studio-packs`
(plus existing domains and `auth` / `platform` / `mercado-pago` / `deployment`)
