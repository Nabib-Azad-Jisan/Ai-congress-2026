# Free email verification using Gmail

This app can send verification codes through a regular Gmail account using SMTP. No separate paid email provider or custom domain is required. Google account eligibility, anti-abuse controls and sending limits still apply; this is suited to a small local demo. See [Google App Password requirements](https://support.google.com/accounts/answer/185833) and [Gmail sending limits](https://support.google.com/mail/answer/22839).

## Private sender setup

1. Sign into the Gmail account you want to send from.
2. Enable Google 2-Step Verification if needed. Open [App Passwords](https://myaccount.google.com/apppasswords) and create one called **AgroSphere AI**. Some managed or specially protected accounts do not offer App Passwords.
3. From the repository root in your own PowerShell terminal, run:

```powershell
.\.venv\Scripts\python.exe scripts/configure_email.py --configure --sender YOUR_ADDRESS@gmail.com
.\.venv\Scripts\python.exe scripts/configure_email.py --check
```

Enter the 16-letter App Password into the hidden prompt. Do not enter your normal Google password or put the App Password into chat. The script writes the ignored root `.env`, preserves the existing private identity encryption key, selects SMTP email and disables SMS. `--init --sender ...` only prepares settings; it does not enter or validate an App Password. Creating the password in Google alone does not configure the project.

The `--check` command logs into Gmail SMTP without sending email. A successful login establishes sender access; actual mailbox delivery still needs a code request and confirmation. Restart API/worker processes and reload the sign-in screen after configuration. Service environment variables take precedence over the root `.env`.

Use **Sign up** for a new email address; **Sign in** sends codes only for existing eligible verified accounts. New customers/farmers keep the same roles, private signup details and password sign-in as before. A phone number is not needed for email signup. Ineligible account requests receive a generic response without sending an email, to avoid exposing registered addresses.

## Storage and limits

Migration `0007` adds `email_verifications` to the shared database. Each challenge has a random ID, a keyed SHA-256 digest, contact/purpose binding, 10-minute expiry, five-attempt limit and consumed state. Raw codes are never returned by the API or stored in the database. A successful code check is consumed in the same transaction that creates the account/session; concurrent checks cannot reuse it. Resending invalidates earlier codes for that contact/purpose after successful SMTP submission. Submission failures do not create a usable challenge. Expired challenges older than a day are removed during later successful starts.

Email-only configuration uses `AUTH_EMAIL_PROVIDER=smtp` and `ENABLE_SMS_VERIFICATION=0`. Existing Twilio credentials remain inactive for delivery. The browser chooses email from server capabilities and disables SMS. The base send/check rate limits remain in force. Gmail may reject sending because of its own limits or account rules; SMTP acceptance is not proof that a message reached the inbox rather than spam.

Back up the database, private media and `SIGNUP_DATA_KEY` together. Changing the encryption key makes prior signup identity data unreadable and invalidates outstanding email-code digests. Changing only the Gmail App Password does not rotate that key. Keep all SMTP values on the backend; never use `NEXT_PUBLIC_*` for credentials.

Other SMTP services can use `SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS_MODE` (`ssl` or `starttls`), `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM`. This Gmail helper intentionally configures `smtp.gmail.com:465` with certificate-verified TLS.
