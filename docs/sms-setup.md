# Enable real SMS verification locally

This checkout uses Twilio Verify. A disabled button means delivery or encrypted signup storage is not configured; changing a valid phone number will not enable it. No development code or simulated delivery enables real signup.

1. Create/sign in to your [Twilio account](https://console.twilio.com/). Complete the account's verification steps yourself.
2. In **Verify > Services**, create a verification service and copy its Service SID (`VA...`). Follow the [Verify quickstart](https://www.twilio.com/docs/verify/quickstarts).
3. Create an API key authorized for that service, and keep its SID (`SK...`) and secret. [Verify API authentication](https://www.twilio.com/docs/verify/api) uses this SID as the username and secret as the password.
4. In **Verify > Settings > Geo permissions**, allow Bangladesh (`+880`) for SMS. Use [Verify Geo Permissions](https://www.twilio.com/docs/verify/preventing-toll-fraud/verify-geo-permissions), which is separate from Programmable Messaging permissions.
5. For a trial account, verify the destination phone number in Twilio Console first. Trial restrictions and eligibility apply; see [Twilio's Verify prerequisites](https://www.twilio.com/docs/verify/api/verification).

From the repository root in your own terminal, run:

```powershell
.\.venv\Scripts\python.exe scripts/configure_sms.py --configure
.\.venv\Scripts\python.exe scripts/configure_sms.py --check
```

If you have an Account SID and Auth Token instead of an API key, use `--configure --account-token`. This stores `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` privately. The backend supports either pair; a complete API key pair takes precedence. API keys are preferable for deployed services. Change pasted/exposed tokens in Twilio Console, then update the local file and restart the API.

The first command prompts for each credential without displaying it, stores them in the ignored root `.env`, and generates a stable Fernet encryption key if one does not exist. Keep that key with your database backups: replacing it makes existing private signup details unreadable. Do not paste credentials into chat or put them in `NEXT_PUBLIC_*` settings. Existing process environment values take priority over `.env`.

The check reads the Twilio service and sends **no SMS**. It confirms service access, not handset delivery, destination permissions, or account credit. Restart the API and marketplace worker afterward, and reload the sign-in page. API, Alembic, and worker processes load the root `.env` automatically; hosting environment settings remain authoritative.

```powershell
cd apps/api
..\..\.venv\Scripts\python.exe -m alembic upgrade head
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# In another terminal, from apps/api:
..\..\.venv\Scripts\python.exe -m app.market_worker
```

Then open the app, select **Sign up**, enter your details and phone number, and request a real verification code. With the fixed `+880` prefix, enter the remaining 10 digits starting with `1`. Sign-in codes only go to existing eligible accounts; responses intentionally do not reveal whether a contact is registered. Codes are checked by Twilio before a new account/session is committed to the database.

Email is a separate channel and additionally requires Twilio Verify's SendGrid integration. Configuring SMS credentials alone does not prove email delivery. Hosted or Docker services need the same settings injected into the API environment; do not upload the private local `.env` with source code.

## Current local database

The native Windows run uses `apps/api/agrosphere.db` (SQLite), accessed through SQLAlchemy. All personal modules and marketplace tables share that database. `records.kind` distinguishes farms, plots, cases, weather snapshots, comparisons, actions, history, and AgroRescue decisions. Marketplace orders, products, carts and bids have dedicated relational tables. Images are private files under `apps/api/storage`; back up the database, media and private-data key together. The browser holds session/plot-selection state, not the application database.

Alembic migration `0006` creates the current schema. SQLite is appropriate for this local run. The repository also supports PostgreSQL through `DATABASE_URL` and Compose; this local run is not using PostgreSQL. Moving to it requires an explicit data migration, not merely changing the connection string.
