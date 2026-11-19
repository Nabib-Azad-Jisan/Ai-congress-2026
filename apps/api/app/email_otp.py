"""SMTP delivery and persistent, single-use email verification challenges."""
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import hashlib
import hmac
import os
import secrets
import smtplib
import ssl

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import delete, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import EmailVerification


def clock():
    return datetime.now(timezone.utc)


def smtp_settings():
    username = os.getenv('SMTP_USERNAME', '').strip()
    sender = os.getenv('SMTP_FROM', username).strip()
    host = os.getenv('SMTP_HOST', '').strip()
    mode = os.getenv('SMTP_TLS_MODE', 'ssl').strip()
    try:
        port = int(os.getenv('SMTP_PORT', '465' if mode == 'ssl' else '587'))
    except ValueError:
        port = 0
    password = os.getenv('SMTP_PASSWORD', '')
    if (not all((host, username, sender, password)) or mode not in {'ssl', 'starttls'}
            or not 0 < port < 65536 or '@' not in sender
            or any(c in host + username + sender for c in '\r\n')):
        raise HTTPException(503, 'Email verification is not configured on this server')
    return host, port, mode, username, password, sender


def smtp_ready() -> bool:
    try:
        smtp_settings()
        Fernet(os.environ['SIGNUP_DATA_KEY'].encode('ascii'))
        return True
    except (HTTPException, KeyError, ValueError, UnicodeError):
        return False


def smtp_connection(settings):
    host, port, mode, username, password, _ = settings
    context = ssl.create_default_context()
    client = (smtplib.SMTP_SSL(host, port, context=context, timeout=10)
              if mode == 'ssl' else smtplib.SMTP(host, port, timeout=10))
    try:
        if mode == 'starttls':
            client.ehlo()
            client.starttls(context=context)
            client.ehlo()
        client.login(username, password)
        return client
    except Exception:
        client.close()
        raise


def send_code(contact: str, code: str) -> None:
    settings = smtp_settings()
    message = EmailMessage()
    message['Subject'] = 'Your AgroSphere AI verification code'
    message['From'] = settings[5]
    message['To'] = contact
    message.set_content(
        f'Your AgroSphere AI verification code is: {code}\n\n'
        'This code expires in 10 minutes. Do not share it with anyone.\n'
        'If you did not request this email, you can ignore it.\n\n'
        'এই যাচাই কোডটি ১০ মিনিট পর্যন্ত ব্যবহার করা যাবে। কাউকে কোডটি দেবেন না।\n'
    )
    try:
        with smtp_connection(settings) as client:
            refused = client.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
    except (smtplib.SMTPException, OSError):
        raise HTTPException(503, 'Email delivery failed. Please try again later or contact the site operator.') from None


def digest(challenge_id: str, contact: str, purpose: str, code: str) -> str:
    key = os.environ['SIGNUP_DATA_KEY'].encode('ascii')
    payload = '\0'.join(('agrosphere-email-otp-v1', challenge_id, contact, purpose, code)).encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def start_email(db: Session, contact: str, purpose: str) -> str:
    if not smtp_ready():
        raise HTTPException(503, 'Email verification is not configured on this server')
    challenge_id = 'EM' + secrets.token_hex(16)
    code = f'{secrets.randbelow(1_000_000):06d}'
    expires_at = (clock() + timedelta(minutes=10)).isoformat()
    # Do not invalidate earlier codes if submission to the mail server fails.
    send_code(contact, code)
    try:
        db.execute(update(EmailVerification).where(
            EmailVerification.contact == contact, EmailVerification.purpose == purpose,
            EmailVerification.consumed.is_(False),
        ).values(consumed=True))
        db.execute(delete(EmailVerification).where(
            EmailVerification.expires_at < (clock() - timedelta(days=1)).isoformat()))
        db.add(EmailVerification(id=challenge_id, contact=contact, purpose=purpose,
                                 code_digest=digest(challenge_id, contact, purpose, code),
                                 expires_at=expires_at, attempts=0, consumed=False))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, 'Could not save the verification request. Please request a new code.') from None
    return challenge_id


def consume_email(db: Session, challenge_id: str, contact: str, purpose: str, code: str) -> None:
    """Correct consumption commits atomically with account/session creation."""
    invalid = HTTPException(401, 'The code is invalid, expired, or has already been used')
    row = db.get(EmailVerification, challenge_id)
    now = clock().isoformat()
    if (not row or row.contact != contact or row.purpose != purpose
            or row.consumed or row.attempts >= 5 or row.expires_at <= now):
        raise invalid
    eligible = (
        EmailVerification.id == challenge_id, EmailVerification.contact == contact,
        EmailVerification.purpose == purpose, EmailVerification.consumed.is_(False),
        EmailVerification.attempts < 5, EmailVerification.expires_at > now,
    )
    if not hmac.compare_digest(row.code_digest, digest(challenge_id, contact, purpose, code)):
        db.execute(update(EmailVerification).where(*eligible).values(attempts=EmailVerification.attempts + 1))
        db.commit()
        raise invalid
    changed = db.execute(update(EmailVerification).where(*eligible).values(consumed=True))
    if changed.rowcount != 1:
        raise invalid
