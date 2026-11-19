# Free email verification

The user authorized finding and setting up a free alternative to paid SMS, then selected Gmail as the sender. Use Gmail SMTP with a privately entered Google App Password. This uses a regular Gmail account, requires 2-Step Verification, and remains subject to Google's sending limits and account eligibility. No paid plan, domain purchase, or live SMS is part of this change.

## Approach

Considered a transactional email provider free tier (requires another account/sender approval, sometimes a domain), Gmail SMTP (existing account, no separate subscription, limited sending volume), and unverified password signup (does not establish contact ownership). Gmail SMTP was selected by the user. Implement the standard SMTP transport so another SMTP provider can be configured without changing authentication logic.

Keep existing farmer/customer signup, private identity encryption, password login, sessions, roles, and shared SQLAlchemy database. Add an additive `0007` migration and an email verification table. Email challenges use random six-digit codes and 128-bit random IDs, a keyed digest bound to contact/purpose/challenge, a 10-minute expiry, five wrong attempts, and transactional single-use consumption with session/account creation. Resending invalidates earlier codes for the same contact/purpose only after successful SMTP submission. Failed delivery creates no usable challenge. Never put a raw code in API responses, database rows, logs, or source files.

Expose available channels and preferred email channel from `/auth/options`. Configure this local app to use SMTP email and disable SMS; retained Twilio support is inactive unless explicitly reenabled. Keep generic account-enumeration responses and current send/check rate limits. Make the frontend choose email automatically, explain unavailable delivery, and preserve demo/password sign-in. Authentication test processes must not load real local credentials.

Provide a private setup command for the sender and App Password, with an authentication-only check that sends no email. The user creates the App Password and enters it locally. Do not read or create Google credentials through UI automation. Live verification testing requires a test recipient selected by the user; do not claim mailbox receipt from SMTP acceptance alone.

## Verification

Test actual API signup/login/session behavior with an intercepted SMTP boundary, including replay, expiry, wrong attempts, purpose/contact binding, resend, failed delivery and transaction behavior. Check English/Bangla email-only forms and configured/unconfigured states. Run the full API, UI unit, type, lint, build and isolated browser suites. Back up the current SQLite database before applying the additive migration; preserve existing records. The downloaded source has no Git metadata, so changes remain in place without Git commits; store source backups and execution notes under ignored `work/gmail-auth`.
