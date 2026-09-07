"""Error taxonomy for WHA.

All exceptions raised by the application subclass WHAError.
"""


class WHAError(Exception):
    """Base exception for all WHA domain errors."""


class ConfigError(WHAError):
    """Missing or malformed configuration."""


class SourceUnavailable(WHAError):
    """Bridge unreachable, dataset missing."""


class InsufficientData(WHAError):
    """Coverage or baseline too thin."""


class ValidationFailed(WHAError):
    """Pydantic rejected a model boundary."""


class LLMUnavailable(WHAError):
    """Endpoint down, timeout, auth failure."""


class BudgetExhausted(WHAError):
    """Interruption or depth budget spent."""


class SafetyIntercept(WHAError):
    """Red flag crossed."""


class PermissionDenied(WHAError):
    """A tool call outside the T1 table, or a T4 attempt from the model."""


class StaleData(WHAError):
    """Last ingest older than INGEST_STALE_REFUSE_HOURS."""
