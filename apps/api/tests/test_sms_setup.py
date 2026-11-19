import os
from pathlib import Path
import subprocess
import sys
import runpy

from cryptography.fernet import Fernet
from dotenv import dotenv_values
import httpx


SCRIPT = Path(__file__).resolve().parents[3] / 'scripts' / 'configure_sms.py'


def run_setup(env_file, action):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('TWILIO_') and key != 'SIGNUP_DATA_KEY'}
    return subprocess.run([sys.executable, str(SCRIPT), '--env-file', str(env_file), action],
                          text=True, capture_output=True, env=env)


def test_initializing_sms_settings_preserves_private_key_and_existing_settings(tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('DATA_MODE=DEMO\n')
    first = run_setup(env_file, '--init')
    assert first.returncode == 0, first.stderr
    values = dotenv_values(env_file)
    key = values['SIGNUP_DATA_KEY']
    Fernet(key.encode())
    second = run_setup(env_file, '--init')
    assert second.returncode == 0, second.stderr
    assert dotenv_values(env_file)['SIGNUP_DATA_KEY'] == key
    assert dotenv_values(env_file)['DATA_MODE'] == 'DEMO'
    assert key not in first.stdout + first.stderr + second.stdout + second.stderr


def test_sms_check_reports_missing_configuration_without_claiming_delivery(tmp_path):
    result = run_setup(tmp_path / '.env', '--check')
    assert result.returncode == 2
    assert 'TWILIO_VERIFY_SERVICE_SID' in result.stdout
    assert 'No SMS was sent' in result.stdout


def test_sms_check_supports_account_credentials_without_exposing_them(tmp_path, monkeypatch, capsys):
    env_file = tmp_path / '.env'
    key = Fernet.generate_key().decode()
    env_file.write_text('TWILIO_VERIFY_SERVICE_SID=VA' + 'a' * 32 + '\n'
                        'TWILIO_ACCOUNT_SID=AC' + 'b' * 32 + '\n'
                        'TWILIO_AUTH_TOKEN=private-test-token\nSIGNUP_DATA_KEY=' + key + '\n')
    for name in list(os.environ):
        if name.startswith('TWILIO_') or name == 'SIGNUP_DATA_KEY':
            monkeypatch.delenv(name)
    script = runpy.run_path(str(SCRIPT))
    requests = []

    def service_get(url, **kwargs):
        requests.append((url, kwargs['auth']))
        return httpx.Response(200, json={'sid': 'VA' + 'a' * 32})

    monkeypatch.setattr(script['httpx'], 'get', service_get)
    assert script['check'](env_file) == 0
    assert requests == [('https://verify.twilio.com/v2/Services/VA' + 'a' * 32,
                         ('AC' + 'b' * 32, 'private-test-token'))]
    output = capsys.readouterr().out
    assert 'private-test-token' not in output and key not in output
    assert 'No SMS was sent' in output
