import os
from pathlib import Path
import runpy
import subprocess
import sys

from cryptography.fernet import Fernet
from dotenv import dotenv_values


SCRIPT = Path(__file__).resolve().parents[3] / 'scripts' / 'configure_email.py'


def test_gmail_setup_preserves_existing_encryption_key_and_disables_sms(tmp_path):
    env_file = tmp_path / '.env'
    key = Fernet.generate_key().decode()
    env_file.write_text('SIGNUP_DATA_KEY=' + key + '\nDATA_MODE=DEMO\n')
    result = subprocess.run([sys.executable, str(SCRIPT), '--env-file', str(env_file),
                             '--init', '--sender', 'sender@gmail.com'], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    values = dotenv_values(env_file)
    assert values['SIGNUP_DATA_KEY'] == key and values['DATA_MODE'] == 'DEMO'
    assert values['AUTH_EMAIL_PROVIDER'] == 'smtp'
    assert values['ENABLE_SMS_VERIFICATION'] == '0'
    assert values['SMTP_HOST'] == 'smtp.gmail.com'
    assert values['SMTP_USERNAME'] == values['SMTP_FROM'] == 'sender@gmail.com'
    assert not values.get('SMTP_PASSWORD')
    assert key not in result.stdout


def test_private_gmail_configuration_never_prints_password(tmp_path, monkeypatch, capsys):
    script = runpy.run_path(str(SCRIPT))
    env_file = tmp_path / '.env'
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), '--env-file', str(env_file), '--configure', '--sender', 'sender@gmail.com'])
    script['main'].__globals__['getpass'] = lambda _: 'abcd efgh ijkl mnop'
    assert script['main']() == 0
    assert dotenv_values(env_file)['SMTP_PASSWORD'] == 'abcdefghijklmnop'
    assert 'abcdefghijklmnop' not in capsys.readouterr().out
