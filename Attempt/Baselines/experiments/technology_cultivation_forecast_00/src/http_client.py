"""Thin re-export shim: Baseline now shares the unified HTTP client from Shared.

This module previously contained its own ``PoliteApiClient``. To eliminate the
two parallel cache formats (16-char hash here vs 64-char hash in Shared) that
caused cache misses and duplicate rate-limited requests, Baseline now imports
the canonical implementation from ``Attempt/Shared/src/http_client.py``.

Existing call sites (`from .http_client import PoliteApiClient`) keep working.

Implementation note: we cannot do ``from http_client import ...`` because this
file itself is named ``http_client.py``, which would create a circular
self-import. Instead we load Shared's module under a distinct name via
``importlib`` and re-export its public symbols.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Shared/src is four parents up + Shared/src.
_ATTEMPT_ROOT = Path(__file__).resolve().parents[4]
_SHARED_SRC = _ATTEMPT_ROOT / "Shared" / "src"
if str(_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(_SHARED_SRC))

_SHARED_HTTP_PATH = _SHARED_SRC / "http_client.py"
_spec = importlib.util.spec_from_file_location("_shared_http_client", _SHARED_HTTP_PATH)
assert _spec is not None and _spec.loader is not None
_shared = importlib.util.module_from_spec(_spec)
# Register before exec so @dataclass can resolve cls.__module__ in sys.modules.
sys.modules["_shared_http_client"] = _shared
_spec.loader.exec_module(_shared)

CachedResponse = _shared.CachedResponse
PoliteApiClient = _shared.PoliteApiClient
RateLimitedError = _shared.RateLimitedError
DEFAULT_HTTP_SETTINGS = _shared.DEFAULT_HTTP_SETTINGS

__all__ = ["CachedResponse", "PoliteApiClient", "RateLimitedError", "DEFAULT_HTTP_SETTINGS"]
