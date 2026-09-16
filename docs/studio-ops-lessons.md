# Studio Ops — lecciones y decisiones de implementación

Specs: `openspec/specs/studio-*.md` (+ `studio-aranceles`).  
Active change: `studio-aranceles`.  
Alembic head: **016**.

## Convivencia

- Estudio no alimenta cierres ni reemplaza SigueFit.
- Admin: Cierres + Estudio; instructor/alumno: stubs mientras pause.

## Pause

- `STUDIO_SCHEDULE_PAUSED` (default true): series/sesiones/book/waitlist/attendance → 410.
- Carve-out: calendar availability/schedule/enroll + **aranceles/abonos**.

## Calendario

- Enroll puntual sin abono (`abono_id` null); cobertura se asocia después al abono.

## Aranceles / abonos (en implementación)

- Catálogo: actividades + valor + clases/semana.
- Abono: mes móvil (mismo día +1 mes); hasta N series; pago parcial; turnos elegibles a mano.
- Packs/créditos **eliminados** (mig 016).

## Alumnos

- Email unificado; Editar/Eliminar; botón **Abonos**.
