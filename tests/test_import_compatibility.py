"""Exercise package imports in fresh processes, without an optional backport."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("remove_legacy_export", [False, True])
def test_package_import_and_registry_without_resources_backport(remove_legacy_export):
    if remove_legacy_export and sys.version_info < (3, 11):
        pytest.skip("The replacement stdlib resources ABCs require Python 3.11+")

    script = f"""
import importlib.abc
import sys

# Keep this independent of whether a developer installed the optional backport.
sys.modules['importlib_resources'] = None
if {remove_legacy_export!r} and hasattr(importlib.abc, 'Traversable'):
    del importlib.abc.Traversable

import kie_api
registry = kie_api.load_registry()
assert registry.get_model('nano-banana-2').provider_model == 'nano-banana-2'
print('registry loaded')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "registry loaded"
