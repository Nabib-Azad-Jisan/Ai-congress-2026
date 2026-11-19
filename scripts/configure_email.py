"""Configure a free Gmail SMTP sender privately. --check never sends email."""
import argparse
from getpass import getpass
import os
from pathlib import Path
import re
import smtplib
import ssl

from cryptography.fernet import Fernet
from dotenv import dotenv_values, set_key


ROOT = Path(__file__).resolve().parents[1]


def initialize(path: Path, sender: str, password: str | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    values = dotenv_values(path)
    key = os.getenv('SIGNUP_DATA_KEY') or values.get('SIGNUP_DATA_KEY')
    if key:
        Fernet(key.encode('ascii'))
    else:
        set_key(str(path), 'SIGNUP_DATA_KEY', Fernet.generate_key().decode())
    settings = {
        'AUTH_EMAIL_PROVIDER': 'smtp', 'ENABLE_SMS_VERIFICATION': '0',
        'SMTP_HOST': 'smtp.gmail.com', 'SMTP_PORT': '465', 'SMTP_TLS_MODE': 'ssl',
        'SMTP_USERNAME': sender, 'SMTP_FROM': sender,
    }
    if password is not None:
        settings['SMTP_PASSWORD'] = password
    elif 'SMTP_PASSWORD' not in values:
        settings['SMTP_PASSWORD'] = ''
    for name, value in settings.items():
        set_key(str(path), name, value)


def check(path: Path) -> int:
    values = {**dotenv_values(path), **os.environ}
    missing = [name for name in ('SMTP_USERNAME', 'SMTP_PASSWORD', 'SIGNUP_DATA_KEY') if not values.get(name)]
    if missing:
        print('Missing settings: ' + ', '.join(missing) + '. No email was sent.')
        return 2
    try:
        Fernet(values['SIGNUP_DATA_KEY'].encode('ascii'))
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context, timeout=15) as client:
            client.login(values['SMTP_USERNAME'], values['SMTP_PASSWORD'])
    except (ValueError, UnicodeError, smtplib.SMTPException, OSError):
        print('Gmail authentication failed. Check the sender and Google App Password. No email was sent.')
        return 2
    print('Gmail SMTP authentication succeeded. No email was sent.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--sender', help='The Gmail account that sends verification codes')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--init', action='store_true', help='Prepare Gmail settings, leaving any existing App Password intact')
    action.add_argument('--configure', action='store_true', help='Enter the Google App Password without displaying it')
    action.add_argument('--check', action='store_true', help='Validate Gmail authentication without sending email')
    args = parser.parse_args()
    path = args.env_file.resolve()
    if args.check:
        return check(path)
    sender = (args.sender or dotenv_values(path).get('SMTP_USERNAME') or input('Sender Gmail address: ')).strip().lower()
    if not re.fullmatch(r'[^\s@]+@gmail\.com', sender):
        print('Enter a valid @gmail.com sender address; no settings were changed.')
        return 2
    password = None
    if args.configure:
        password = getpass('Google App Password (hidden; not your normal password): ').replace(' ', '').strip()
        if not re.fullmatch(r'[a-zA-Z]{16}', password):
            print('Use the 16-letter Google App Password; no settings were changed.')
            return 2
    try:
        initialize(path, sender, password)
    except (ValueError, UnicodeError):
        print('The existing private-data key is invalid. Restore it; it was not replaced.')
        return 2
    print('Gmail settings saved privately. SMS is disabled. No password was printed.')
    print('Restart the API and reload the sign-in page after entering the App Password.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
