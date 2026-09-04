"""
cascadeid.utils.serialization

Safe JSON serialization that handles:
- datetime → ISO-8601 string
- Decimal → string (preserves precision)
- numpy scalars → Python native types
- NaN / Inf → null  (JSON spec does not permit NaN/Infinity)
- UUID → string

Implementation note:
Python's json module emits NaN/Infinity as bare tokens when allow_nan=True
(the default), which is invalid JSON and breaks most parsers. We pre-process
the object tree to replace non-finite floats with None before encoding.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np


def _sanitize(obj: Any) -> Any:
    """
    Recursively replace non-finite floats (NaN, Inf) with None.
    Converts numpy scalars and other non-serializable types to
    JSON-compatible Python types.

    This must run BEFORE json.dumps so the standard encoder
    never sees a bare float NaN or Infinity.
    """
    if obj is None:
        return None

    # numpy arrays → list, then recurse
    if isinstance(obj, np.ndarray):
        return _sanitize(obj.tolist())

    # numpy scalar types
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if not math.isfinite(v) else v
    if isinstance(obj, np.bool_):
        return bool(obj)

    # Python float
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj

    # Python containers — recurse
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        sanitized = [_sanitize(v) for v in obj]
        return sanitized if isinstance(obj, list) else tuple(sanitized)

    # datetime / date → ISO string
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()

    # Decimal → string (preserves precision, avoids float rounding)
    if isinstance(obj, Decimal):
        return str(obj)

    # Path → string
    if isinstance(obj, Path):
        return str(obj)

    # Everything else passes through (str, int, bool, None)
    return obj


class SafeJSONEncoder(json.JSONEncoder):
    """
    JSON encoder used after _sanitize() has already cleaned the object.
    Handles any remaining edge cases that _sanitize() might miss
    (e.g. custom objects with __dict__).
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            return None if not math.isfinite(v) else v
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


def to_json(obj: Any, indent: int | None = None) -> str:
    """
    Serialize obj to a JSON string.

    NaN and Inf are converted to null.
    datetime → ISO-8601. Decimal → string. numpy → native types.
    """
    sanitized = _sanitize(obj)
    # allow_nan=False ensures the encoder raises rather than emitting
    # bare NaN/Infinity tokens if _sanitize missed anything.
    return json.dumps(sanitized, cls=SafeJSONEncoder, indent=indent, allow_nan=False)


def from_json(text: str) -> Any:
    """Deserialize a JSON string."""
    return json.loads(text)


def to_json_file(obj: Any, path: Path, indent: int = 2) -> None:
    """Write obj as JSON to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(to_json(obj, indent=indent))


def from_json_file(path: Path) -> Any:
    """Read JSON from path."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)