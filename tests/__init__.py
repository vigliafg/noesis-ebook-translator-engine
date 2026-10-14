"""Test bootstrap: isolate config/cache before the monofile is imported."""
import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="noesis-et-engine-tests-")
os.environ.setdefault("NOESIS_CONFIG_DIR", _TMP)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
