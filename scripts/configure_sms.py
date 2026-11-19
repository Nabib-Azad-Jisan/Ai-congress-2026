"""Prepare private Twilio settings; --check validates access without sending SMS."""
import argparse
from getpass import getpass
import os
from pathlib import Path
import re

from cryptography.fernet import Fernet
from dotenv import dotenv_values, set_key
import httpx


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_KEYS = ('TWILIO_VERIFY_SERVICE_SID', 'TWILIO_API_KEY_SID', 'TWILIO_API_KEY_SECRET')
ACCOUNT_KEYS = ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN')


def initialize(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    values = dotenv_values(path)
    # Keep the same key: replacing it would make existing identity data unreadable.
    key = os.getenv('SIGNUP_DATA_KEY') or values.get('SIGNUP_DATA_KEY')
    if key:
        Fernet(key.encode('ascii'))
    else:
        set_key(str(path), 'SIGNUP_DATA_KEY', Fernet.generate_key().decode('ascii'))
    for name in (*PROVIDER_KEYS, *ACCOUNT_KEYS):
        if name not in values:
            set_key(str(path), name, '')


def check(path: Path) -> int:
    values = {**dotenv_values(path), **os.environ}
    missing = [name for name in (PROVIDER_KEYS[0], 'SIGNUP_DATA_KEY') if not values.get(name)]
    if values.get(PROVIDER_KEYS[1]) and values.get(PROVIDER_KEYS[2]):
        username, secret = (values[name] for name in PROVIDER_KEYS[1:])
        username_pattern = r'SK[0-9a-fA-F]{32}'
    elif all(values.get(name) for name in ACCOUNT_KEYS):
        username, secret = (values[name] for name in ACCOUNT_KEYS)
        username_pattern = r'AC[0-9a-fA-F]{32}'
    else:
        missing.append('TWILIO_API_KEY_SID + TWILIO_API_KEY_SECRET or TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN')
    if missing:
        print('Missing settings: ' + ', '.join(missing) + '. No SMS was sent.')
        return 2
    service = values[PROVIDER_KEYS[0]]
    if not re.fullmatch(r'VA[0-9a-fA-F]{32}', service) or not re.fullmatch(username_pattern, username):
        print('Use a Verify Service SID (VA...) and the matching API Key SID (SK...) or Account SID (AC...). No SMS was sent.')
        return 2
    try:
        Fernet(values['SIGNUP_DATA_KEY'].encode('ascii'))
    except (ValueError, UnicodeError):
        print('SIGNUP_DATA_KEY is invalid. Restore the original key; do not rotate it. No SMS was sent.')
        return 2
    try:
        response = httpx.get(f'https://verify.twilio.com/v2/Services/{service}',
                             auth=(username, secret), timeout=15)
        if response.status_code != 200:
            print(f'Twilio service check failed (HTTP {response.status_code}). Check credentials and service access. No SMS was sent.')
            return 2
        if response.json().get('sid') != service:
            raise ValueError('Unexpected service response')
    except (httpx.HTTPError, ValueError):
        print('Could not validate the Twilio service. Check network access and retry. No SMS was sent.')
        return 2
    print('Twilio Verify service access confirmed. No SMS was sent.')
    print('Also enable Bangladesh in Verify Geo Permissions and verify your recipient if using a trial account.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--init', action='store_true', help='Prepare blank provider settings and a stable private-data key')
    action.add_argument('--configure', action='store_true', help='Prompt privately for Twilio credentials')
    action.add_argument('--check', action='store_true', help='Read the Verify service; never send a code')
    parser.add_argument('--account-token', action='store_true', help='Use Account SID/Auth Token with --configure')
    args = parser.parse_args()
    if args.account_token and not args.configure:
        parser.error('--account-token requires --configure')
    path = args.env_file.resolve()
    if args.check:
        return check(path)
    credentials = {}
    if args.configure:
        username_key, secret_key = ACCOUNT_KEYS if args.account_token else PROVIDER_KEYS[1:]
        username_pattern = r'AC[0-9a-fA-F]{32}' if args.account_token else r'SK[0-9a-fA-F]{32}'
        for name, pattern in [(PROVIDER_KEYS[0], r'VA[0-9a-fA-F]{32}'),
                              (username_key, username_pattern),
                              (secret_key, r'[^\r\n]+')]:
            value = getpass(name + ' (hidden): ').strip()
            if not re.fullmatch(pattern, value):
                print(f'Invalid {name}; no settings were changed.')
                return 2
            credentials[name] = value
        # An older complete API key pair would otherwise take precedence.
        if args.account_token:
            credentials.update({name: '' for name in PROVIDER_KEYS[1:]})
    try:
        initialize(path)
    except (ValueError, UnicodeError):
        print('The existing private-data key is invalid. Restore it before continuing; it was not replaced.')
        return 2
    for name, value in credentials.items():
        set_key(str(path), name, value)
    print('Private settings saved to ' + str(path) + '. Credentials were not printed.')
    print('Restart the API and marketplace worker after configuring credentials, then reload the sign-in page.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
