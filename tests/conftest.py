import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
NODE = shutil.which("node")


def run_node(*args) -> dict:
    if not NODE:
        pytest.skip("node not installed")
    res = subprocess.run([NODE, *map(str, args)], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(res.stdout)


@pytest.fixture(scope="session")
def reference():
    return json.loads((DATA / "reference.json").read_text(encoding="utf-8"))
