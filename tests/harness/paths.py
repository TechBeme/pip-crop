"""Where the test harness reads and writes files. Everything it produces
(profiles, screenshots, calibration, results) goes to tests/out/, or to
$PIPCROP_TEST_OUT when set."""
import os
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
TESTS = HARNESS.parent
REPO = TESTS.parent
WWW = TESTS / "www"
JS = HARNESS / "js"
OUT = Path(os.environ.get("PIPCROP_TEST_OUT") or TESTS / "out")
SHOTS = OUT / "shots"
PROFILES = OUT / "profiles"
DIST = REPO / "dist"
# The module the tests inject (tests/e2e/*.py without PIPCROP_NO_INJECT=1).
MODULE_URL = (REPO / "src" / "pipcrop.js").as_uri()

SHOTS.mkdir(parents=True, exist_ok=True)
PROFILES.mkdir(parents=True, exist_ok=True)
