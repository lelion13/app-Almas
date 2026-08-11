# Delta: Studio Students & Bookings

## ADDED Requirements

### Requirement: Student profiles

Admin MUST CRUD students with personal data, contact, emergency contact, medical notes. A student MAY be linked to a User with role `alumno`.

### Requirement: Fixed and mobile enrollment

- **Fixed:** admin assigns a student to a recurring slot; system books future instances (subject to pack credits and capacity) as designed (e.g. rolling window).
- **Mobile:** alumno (or admin) books individual session instances week by week, seeing remaining capacity in real time.

Booking MUST require an active pack with remaining credits and valid sede scope for that session’s sede.

#### Scenario: Full class rejects booking
- **GIVEN** a session at capacity
- **WHEN** a mobile book is attempted
- **THEN** the system MUST reject booking and MAY offer waitlist join

### Requirement: Cancel booking and credit return

Alumno MUST cancel their own booking and recover one credit to the pack. Admin MUST cancel any booking; instructor MUST cancel bookings on their sessions. Credits MUST return unless a more specific policy (e.g. already marked no-show deducted) applies.

#### Scenario: Alumno cancel returns credit
- **GIVEN** an alumno with a future booking consuming a credit
- **WHEN** they cancel
- **THEN** the booking MUST be cancelled and pack remaining credits MUST increase by one

### Requirement: Waitlist

When a session is full, alumno or admin MUST be able to join a waitlist (ordered). When a spot frees, the system MUST **not** auto-enroll. The free spot MUST be visible in-app; **alumno or admin confirms** enrollment, which then consumes a credit if successful.

#### Scenario: Confirm from waitlist
- **GIVEN** a free spot and a waitlisted alumno with credits
- **WHEN** alumno or admin confirms
- **THEN** a booking MUST be created and waitlist entry removed

### Requirement: Attendance and lost-class policy

Instructor (own sessions) and admin MUST set attendance: `presente` | `ausente` | `tarde`. Configurable no-show/lost-class policy MUST determine whether an absent without timely cancel deducts a credit (config flag/default documented). MVP has **no** timed reschedule; cancel is the student self-serve path.

#### Scenario: Mark ausente
- **GIVEN** a session booking
- **WHEN** instructor marks `ausente`
- **THEN** attendance MUST persist and lost-class policy MUST be applied if configured to deduct
