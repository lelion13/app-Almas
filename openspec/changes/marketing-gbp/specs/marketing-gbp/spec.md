# Marketing GBP (Telegram + Google Business Profile)

## Purpose

Operate a single Google Business Profile location via Telegram: create local posts and handle reviews (Pub/Sub alerts, auto-reply for 5-star empty reviews, manual reply). Admin connects GBP with OAuth in Almas; day-to-day operations stay in Telegram.

## Requirements

### Requirement: GBP OAuth connect (admin)

Admin MUST connect Google Business Profile using OAuth 2.0 with offline access and scope `https://www.googleapis.com/auth/business.manage` (or current equivalent documented by Google). Access and refresh tokens MUST be encrypted at rest (same secrecy rules as Mercado Pago tokens). Tokens MUST NEVER be logged or returned to the client.

Admin UI MUST expose a connect/disconnect (or reconnect) flow. Only role `admin` MUST access OAuth start and account status endpoints.

Location account/location resource names (or IDs) for the single V1 location MUST come from environment configuration.

#### Scenario: Admin connects GBP
- **GIVEN** an authenticated admin and valid Google OAuth app credentials
- **WHEN** the admin completes the OAuth consent for the GBP manager account
- **THEN** the system MUST store encrypted tokens and mark GBP as connected

#### Scenario: Non-admin blocked
- **GIVEN** a non-admin user
- **WHEN** they call GBP OAuth start
- **THEN** the response MUST be `403`

### Requirement: Telegram authorization

Telegram updates that create posts or reply to reviews MUST be accepted only from Telegram user IDs listed in environment allowlist. Other users MUST be ignored or rejected with no GBP side effect.

Review alerts MUST be sent to a fixed `TELEGRAM_ADMIN_CHAT_ID` from environment.

Telegram webhook endpoint MUST validate the request authenticity (bot secret token header and/or path secret as configured) before processing.

#### Scenario: Unauthorized user ignored
- **GIVEN** a Telegram update from a user_id not in the allowlist
- **WHEN** the webhook receives a photo intended as a post
- **THEN** the system MUST NOT create a GBP local post

### Requirement: Publish GBP local posts from Telegram

Authorized users MUST be able to create a GBP local post by sending either:
- a photo with optional caption, or
- a text-only message (no photo)

The system MUST map that content to GBP `localPosts.create` for the configured location. On success or failure the bot MUST notify the admin chat (or the sender) with a clear result.

#### Scenario: Text-only post
- **GIVEN** an allowlisted user and connected GBP
- **WHEN** they send a text-only message intended as a post
- **THEN** the system MUST create a GBP local post with that text

#### Scenario: Photo post
- **GIVEN** an allowlisted user and connected GBP
- **WHEN** they send a photo with caption
- **THEN** the system MUST upload/media-handle as required by GBP and create a local post

### Requirement: Pub/Sub push for new reviews

The system MUST expose `POST /api/v1/marketing/google-pubsub-webhook` to receive Google Cloud Pub/Sub push messages for new GBP reviews. The endpoint MUST verify that the request is an authorized Pub/Sub push (OIDC token and/or shared verification as configured) before trusting the payload.

#### Scenario: Unauthorized push rejected
- **GIVEN** a POST without valid Pub/Sub authentication
- **WHEN** the webhook is called
- **THEN** the system MUST reject with `401` or `403` and MUST NOT write reviews or call Telegram/GBP

### Requirement: Persist reviews

On a valid new-review notification the system MUST upsert a review row keyed by Google `review_id` (or equivalent stable id) including at least: star rating, reviewer display name when available, comment text (nullable), created time, reply status (`pending` | `auto_replied` | `manual_replied` | `skipped`), and optional reply text/timestamps.

Duplicate notifications for the same `review_id` MUST be idempotent (no duplicate Telegram spam; no double reply).

#### Scenario: Duplicate Pub/Sub delivery
- **GIVEN** a review already stored and processed
- **WHEN** the same review notification is delivered again
- **THEN** the system MUST NOT send a second alert as if new and MUST NOT post a second GBP reply

### Requirement: Telegram alert for new reviews

For each newly ingested review the system MUST send a structured Telegram message to `TELEGRAM_ADMIN_CHAT_ID` including stars, author (when available), and text (or indication of empty text), plus a **Responder** action for manual reply when auto-reply does not apply or as allowed by design for non-auto cases.

#### Scenario: New review with text
- **GIVEN** a new 4-star review with comment text
- **WHEN** Pub/Sub delivers the notification
- **THEN** Telegram admin chat MUST receive an alert with stars, author, text, and a Responder control

### Requirement: Auto-reply 5 stars empty text

WHEN a new review has rating **5** and empty/missing comment text, the system MUST:
1. Choose a thank-you phrase at random from a fixed in-code/config list
2. Call GBP `reviews.reply` with that phrase
3. Update the stored review status to `auto_replied`
4. Notify Telegram admin chat that auto-reply was sent

Reviews that are not 5★ empty MUST NOT be auto-replied in V1.

#### Scenario: Five stars no text
- **GIVEN** a new 5-star review with no comment
- **WHEN** the notification is processed
- **THEN** GBP MUST receive an auto reply AND Telegram MUST be notified of the auto action

#### Scenario: Five stars with text
- **GIVEN** a new 5-star review with comment text
- **WHEN** the notification is processed
- **THEN** the system MUST alert Telegram and MUST NOT auto-reply

### Requirement: Manual reply via Telegram

Authorized users MUST start a manual reply using the **Responder** control on an alert. The bot MUST then accept the next text message from that user as the reply body (with a clear cancel path), publish it via GBP `reviews.reply`, update review status to `manual_replied`, and confirm in Telegram.

Unauthorized users MUST NOT be able to complete a manual reply.

#### Scenario: Manual reply success
- **GIVEN** an allowlisted admin who pressed Responder on a review alert
- **WHEN** they send the reply text
- **THEN** GBP MUST store the reply and the DB status MUST become `manual_replied`

### Requirement: Pause and public endpoints

Marketing Telegram and Pub/Sub webhooks MUST remain reachable without JWT (public HTTPS) but MUST enforce their own auth validations. GBP OAuth management endpoints MUST require admin JWT.

## Out of scope (this change)

- Public marketing landing page
- Multiple GBP locations / Studio site mapping
- Full web UI for listing/editing reviews
- Edit or delete GBP posts from Telegram
- Automatic replies for ratings other than 5★ empty text
- Association with Mercado Pago or abonos
