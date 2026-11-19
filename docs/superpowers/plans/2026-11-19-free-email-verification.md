# Free Email Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable free Gmail email-code signup/login while preserving the project's database and roles.

**Architecture:** Standard-library SMTP sends codes; SQLAlchemy persists keyed challenges in the shared database. Existing OTP routes dispatch to SMTP email or retained Twilio support according to explicit configuration. The UI reflects per-channel availability.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Python smtplib/EmailMessage/HMAC, Next.js/React, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-19-free-email-verification-design.md`

## Global Constraints

- No paid plan, domain purchase, or live SMS is part of this change.
- Keep existing farmer/customer signup, private identity encryption, password login, sessions, roles, and shared SQLAlchemy database.
- Never put a raw code in API responses, database rows, logs, or source files.
- Authentication test processes must not load real local credentials.
- Live verification testing requires a test recipient selected by the user; do not claim mailbox receipt from SMTP acceptance alone.

## Review Focus

- Simultaneous correct code checks must yield at most one session.
- SMTP acceptance followed by database failure must produce an error, not false success.
- Contact, purpose or channel changes must never reuse another challenge.
- Server restart must retain expiry, attempts and consumption state.
- Email-only deployment must never offer an enabled SMS action or call Twilio.

### Task 1: Persist and verify email codes

**Files:** create `apps/api/app/email_otp.py`, `apps/api/migrations/versions/0007_email_verifications.py`, `apps/api/tests/test_email_otp.py`; modify `apps/api/app/db.py`, `apps/api/app/otp_auth.py`.

**Interfaces:** `smtp_ready() -> bool`, `send_code(contact: str, code: str) -> None`, `start_email(db, contact, purpose) -> str`, `consume_email(db, verification_id, contact, purpose, code) -> None`. Existing OTP endpoints retain request/response fields; email IDs use `EM` + 32 hex digits.

- [ ] Write API regressions for SMTP signup/login, encrypted account persistence, expiry, five wrong attempts, replay, binding, resend, SMTP failure and concurrent consumption; observe failures.
- [ ] Implement additive model/migration, secure SMTP submission, keyed challenge generation and transactional compare-and-set consumption. Dispatch routes according to contact/channel configuration and expose channel capabilities.
- [ ] Run the targeted tests, then the full API suite. Inspect every failure and record results.

### Task 2: Email-only user flow and private setup

**Files:** modify `apps/web/src/components/account-access.tsx`, `apps/web/e2e/auth-availability.spec.ts`, `.env.example`, `README.md`; create `scripts/configure_email.py`, `apps/api/tests/test_email_setup.py`, `docs/email-setup.md`.

**Interfaces:** `/auth/options` adds `channels: {email: boolean, sms: boolean}` and `default_channel: 'email' | 'phone'`; legacy option responses remain usable. CLI `--configure` privately prompts for Gmail sender/App Password and preserves the existing encryption key; `--check` validates credentials without sending mail.

- [ ] Write failing browser and setup regressions for preferred email, disabled SMS, unavailable email and private settings preservation.
- [ ] Implement capability-based UI, setup CLI and instructions. Configure `AUTH_EMAIL_PROVIDER=smtp` and `ENABLE_SMS_VERIFICATION=0` locally. User supplies the App Password privately.
- [ ] Run targeted tests, full web unit suite, typecheck, lint, production build and isolated full browser suite. Save reviewable UI screenshots.

### Task 3: Activate and review

- [ ] Back up the SQLite database, apply migration `0007`, restart managed services and verify saved counts/integrity plus health/capabilities.
- [ ] Run a fresh independent code review of this change; fix important issues with regression tests.
- [ ] Check Gmail authentication when credentials exist. Finish a real email verification only with the user's selected recipient and report exactly what was observed.
- [ ] Record checks and remaining external setup in `docs/status.md` and `work/gmail-auth/progress.md`. No Git commit is possible in this source archive.
