import base64
from concurrent.futures import ThreadPoolExecutor
import re
import smtplib
import ssl

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from fastapi.testclient import TestClient

from app import otp_auth
from app.db import Session
from tests.test_platform import client, picture


@pytest.fixture
def mail(monkeypatch):
    for name, value in {
        'AUTH_EMAIL_PROVIDER': 'smtp', 'ENABLE_SMS_VERIFICATION': '0',
        'SMTP_HOST': 'smtp.gmail.com', 'SMTP_PORT': '465', 'SMTP_TLS_MODE': 'ssl',
        'SMTP_USERNAME': 'sender@example.test', 'SMTP_PASSWORD': 'private-app-password',
        'SMTP_FROM': 'sender@example.test', 'SIGNUP_DATA_KEY': Fernet.generate_key().decode(),
    }.items():
        monkeypatch.setenv(name, value)
    messages = []

    class SMTP:
        def __init__(self, host, port, *, context, timeout):
            assert (host, port) == ('smtp.gmail.com', 465)
            assert context.verify_mode == ssl.CERT_REQUIRED

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def login(self, username, password):
            assert (username, password) == ('sender@example.test', 'private-app-password')

        def send_message(self, message):
            messages.append(message)
            return {}

    monkeypatch.setattr(smtplib, 'SMTP_SSL', SMTP)
    monkeypatch.setattr(otp_auth, 'send_limit', otp_auth.AuthLimiter())
    monkeypatch.setattr(otp_auth, 'check_limit', otp_auth.AuthLimiter())

    def unexpected_twilio(*_, **__):
        raise AssertionError('Email-only mode must not call Twilio')

    monkeypatch.setattr(otp_auth.httpx, 'post', unexpected_twilio)
    return messages


def profile():
    return {
        'name': 'Email farmer', 'age': 25, 'role': 'farmer', 'gender': 'female',
        'national_id': '1234567890', 'present_address': 'Dhaka test address',
        'permanent_address': 'Dhaka test address', 'ward_number': '12',
        'photo_base64': base64.b64encode(picture()).decode(),
        'password': 'email-test-password', 'confirm_password': 'email-test-password',
    }


def pending(client, mail, purpose='signup', contact='farmer@example.test'):
    response = client.post('/api/v1/auth/otp/start', json={'contact': contact, 'purpose': purpose})
    assert response.status_code == 200, response.text
    assert mail, 'A successful start must submit an email'
    message = mail[-1]
    assert message['To'] == contact
    assert message['From'] == 'sender@example.test'
    code = re.search(r'\b([0-9]{6})\b', message.get_content()).group(1)
    assert code not in response.text
    sid = response.json()['verification_id']
    assert re.fullmatch(r'EM[0-9a-f]{32}', sid)
    return {'contact': contact, 'purpose': purpose, 'verification_id': sid, 'code': code}


def test_email_signup_and_login_use_shared_private_database(client, mail):
    options = client.get('/api/v1/auth/options').json()
    assert options['channels'] == {'email': True, 'sms': False}
    assert options['default_channel'] == 'email'
    signup = pending(client, mail)
    with Session() as db:
        row = db.execute(text('SELECT code_digest, attempts, consumed FROM email_verifications')).one()
        assert len(row.code_digest) == 64 and row.code_digest != signup['code']
        assert row.attempts == 0 and not row.consumed
    response = client.post('/api/v1/auth/otp/verify', json=signup | {'profile': profile()})
    assert response.status_code == 200, response.text
    token = response.json()['token']
    me = client.get('/api/v1/me', headers={'Authorization': 'Bearer ' + token})
    assert me.json()['email'] == 'farmer@example.test'
    assert me.json()['role'] == 'farmer'
    assert 'national_id' not in me.json()
    assert client.post('/api/v1/auth/otp/verify', json=signup | {'profile': profile()}).status_code == 401
    login = pending(client, mail, 'login')
    assert client.post('/api/v1/auth/otp/verify', json=login).status_code == 200


def test_wrong_email_code_locks_after_five_attempts(client, mail):
    body = pending(client, mail) | {'profile': profile()}
    wrong = '000000' if body['code'] != '000000' else '111111'
    for _ in range(5):
        assert client.post('/api/v1/auth/otp/verify', json=body | {'code': wrong}).status_code == 401
    assert client.post('/api/v1/auth/otp/verify', json=body).status_code == 401
    with Session() as db:
        assert db.execute(text('SELECT attempts FROM email_verifications')).scalar_one() == 5
        assert db.execute(text('SELECT COUNT(*) FROM signup_identities')).scalar_one() == 0


def test_email_code_expires_and_is_bound_to_contact_and_purpose(client, mail):
    body = pending(client, mail)
    assert client.post('/api/v1/auth/otp/verify', json=body | {'contact': 'other@example.test', 'profile': profile()}).status_code == 401
    assert client.post('/api/v1/auth/otp/verify', json=body | {'purpose': 'login'}).status_code == 401
    with Session() as db:
        db.execute(text("UPDATE email_verifications SET expires_at='2000-01-01T00:00:00+00:00'"))
        db.commit()
    assert client.post('/api/v1/auth/otp/verify', json=body | {'profile': profile()}).status_code == 401


def test_resend_invalidates_old_challenge(client, mail):
    first = pending(client, mail) | {'profile': profile()}
    second = pending(client, mail) | {'profile': profile()}
    assert client.post('/api/v1/auth/otp/verify', json=first).status_code == 401
    assert client.post('/api/v1/auth/otp/verify', json=second).status_code == 200


def test_failed_email_submission_does_not_leave_a_usable_challenge(client, mail, monkeypatch):
    def fail(*_, **__):
        raise smtplib.SMTPAuthenticationError(535, b'private provider response')

    monkeypatch.setattr(smtplib, 'SMTP_SSL', fail)
    response = client.post('/api/v1/auth/otp/start', json={'contact': 'farmer@example.test', 'purpose': 'signup'})
    assert response.status_code == 503
    assert 'private provider response' not in response.text
    with Session() as db:
        assert db.execute(text('SELECT COUNT(*) FROM email_verifications')).scalar_one() == 0


def test_unconfigured_email_and_disabled_sms_cannot_send(client, mail, monkeypatch):
    monkeypatch.delenv('SMTP_PASSWORD')
    assert client.get('/api/v1/auth/options').json()['signup'] is False
    for contact in ['farmer@example.test', '+8801712345678']:
        response = client.post('/api/v1/auth/otp/start', json={'contact': contact, 'purpose': 'signup'})
        assert response.status_code == 503
    assert mail == []


def test_concurrent_email_code_checks_issue_only_one_session(client, mail):
    signup = pending(client, mail) | {'profile': profile()}
    assert client.post('/api/v1/auth/otp/verify', json=signup).status_code == 200
    login = pending(client, mail, 'login')
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post('/api/v1/auth/otp/verify', json=login), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 401]


def test_email_challenge_survives_a_new_application_lifespan(client, mail):
    from app.main import app
    body = pending(client, mail) | {'profile': profile()}
    with TestClient(app) as reopened:
        assert reopened.post('/api/v1/auth/otp/verify', json=body).status_code == 200


def test_database_failure_after_smtp_acceptance_is_not_reported_as_success(client, mail, monkeypatch):
    def fail_commit(*_):
        raise SQLAlchemyError('test database failure')

    monkeypatch.setattr(Session.class_, 'commit', fail_commit)
    response = client.post('/api/v1/auth/otp/start', json={'contact': 'farmer@example.test', 'purpose': 'signup'})
    assert response.status_code == 503
    assert 'verification_id' not in response.json()
    assert len(mail) == 1
    with Session() as db:
        assert db.execute(text('SELECT COUNT(*) FROM email_verifications')).scalar_one() == 0
