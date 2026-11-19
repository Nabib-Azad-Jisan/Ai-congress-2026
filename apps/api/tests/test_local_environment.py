"""Exercise startup in a separate checkout without touching local credentials."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_api_loads_checkout_env_from_any_working_directory(tmp_path):
    root = tmp_path / 'checkout'
    package = root / 'apps' / 'api' / 'app'
    package.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / 'app' / '__init__.py'
    shutil.copyfile(source, package / '__init__.py')
    (root / '.env').write_text('AGRO_ENV_FILE_TEST=loaded\nAGRO_ENV_PRIORITY_TEST=file\n')
    env = dict(os.environ, PYTHONPATH=str(package.parent), AGRO_ENV_PRIORITY_TEST='service')
    env.pop('AGRO_ENV_FILE_TEST', None)
    env.pop('PYTHON_DOTENV_DISABLED', None)
    result = subprocess.run([
        sys.executable, '-c',
        "import app,os; print(os.getenv('AGRO_ENV_FILE_TEST')); print(os.getenv('AGRO_ENV_PRIORITY_TEST'))",
    ], cwd=tmp_path, env=env, text=True, capture_output=True, check=True)
    assert result.stdout.splitlines() == ['loaded', 'service']
