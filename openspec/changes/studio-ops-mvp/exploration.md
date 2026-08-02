# Exploration: studio-ops-mvp

## Source
Functional requirements 1–10 for a Pilates/Yoga/Postural center.

## Current Almas (context)
Closings, SigueFit, expenses, teachers, MP Conciliación. Roles today: admin/staff.

## Discovery locked
1. **Coexists** with existing Almas; does not replace SigueFit SoT; closings not fed from studio yet.
2. **MVP = C:** ops + plans/payments + basic student portal. Out: rich reports 6.x, mass blasts 5.2, SMS/WhatsApp. Out: integrations 10.x.
3. **Multi-sede from day one.**
4. **Student portal:** same SPA; role **`alumno`**.
5. **Plan scope:** chosen when assigning — **one sede** or **all sedes**.
6. **Notifications:** none automatic; in-app only.
7. **Plans:** class packs only (N + expiry). No mensual libre.
8. **Enrollment modes:** both fixed and mobile.
9. **Roles:** `admin`, `alumno`, `instructor` (agenda + attendance). `recepción` deferred.
10. **Instructors:** new studio model; link to Teachers catalog later.
11. **Policy / edge:** IN A waitlist, D lost-class, F trial/welcome, G gift/transfer, H holidays/exceptions, I mass cancel, J audit. OUT B check-in, C reschedule limits, E plan freeze.
12. **Cancel booking:** alumno cancels → credit returned; admin/instructor can cancel too.
13. **Waitlist:** no auto-enroll; alumno or admin **confirms** when a spot is free (in-app).
14. **Account provisioning:** **A** — admin creates person + login user with **temporary password**.

## Deferred (explicit)
- Replace SigueFit / feed closings from studio
- recepción role, email/SMS/WhatsApp, online MP checkout, Google Calendar, AFIP
- Rich reports/dashboard, pre-check-in, reschedule caps, plan freeze, mensual libre

## Recommendation
Proceed to proposal → domain specs (studio sites/rooms/activities, students, bookings, packs, auth roles) → design → tasks. Large change; implement in phased tasks within the same OpenSpec change or split apply waves.

## Ready for Proposal
**Yes**
