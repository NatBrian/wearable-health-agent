"""Every facade call returns JSON and never raises across the Kotlin boundary.

Three kinds, enumerated in docs/CONTRACTS.md section 12. A screen shows each in words with
the action available: `unavailable` offers retry or Settings, `invalid` shows the message,
`internal` shows the message and keeps the rest of the screen usable.
"""

from __future__ import annotations

import functools
import json
import logging
import traceback
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from wha.errors import WHAError

logger = logging.getLogger(__name__)

# Service errors that mean "something outside the phone is not there right now".
_UNAVAILABLE_NAMES = {"SourceUnavailable", "ConfigError", "LLMUnavailable", "StaleData"}


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {k: _to_jsonable(getattr(value, k)) for k in value.__dataclass_fields__}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def ok(payload: Any) -> str:
    return json.dumps(_to_jsonable(payload), ensure_ascii=False)


def error(kind: str, message: str) -> str:
    return json.dumps({"error": {"kind": kind, "message": message}}, ensure_ascii=False)


def guarded(fn: Callable[..., Any]) -> Callable[..., str]:
    """Wrap a facade function so it always returns a JSON string."""

    @functools.wraps(fn)
    def inner(*args: Any, **kwargs: Any) -> str:
        try:
            result = fn(*args, **kwargs)
            return result if isinstance(result, str) else ok(result)
        except WHAError as exc:
            kind = "unavailable" if type(exc).__name__ in _UNAVAILABLE_NAMES else "invalid"
            logger.warning("%s: %s", type(exc).__name__, exc)
            return error(kind, str(exc))
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("%s: %s", type(exc).__name__, exc)
            return error("invalid", str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("facade %s failed:\n%s", fn.__name__, traceback.format_exc())
            return error("internal", f"{type(exc).__name__}: {exc}")

    return inner
