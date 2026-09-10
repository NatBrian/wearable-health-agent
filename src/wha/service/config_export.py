"""Configuration enumeration shared by the dashboard API and the phone facade.

Moved here from ``wha.api.app.get_config`` so both clients read the same values from
one place. Same behaviour: every public constant plus the subject's local date.
"""

from typing import Any


def config_export() -> dict[str, Any]:
    """Every public constant, plus the subject's local date.

    Enumerated from the module rather than listed by hand, so a constant added to
    ``wha.constants`` is available to an interface immediately and no client can
    drift away from the code. Names are kept exactly as they appear in the source,
    so a reader can find the constant and its reasoning without a mapping table.
    """
    from wha import constants
    from wha.clock import local_today
    from wha.config import get_settings

    exported: dict[str, Any] = {}
    for name in dir(constants):
        if not name.isupper():
            continue
        value = getattr(constants, name)
        if isinstance(value, str | int | float | bool | list | dict | type(None)):
            exported[name] = value

    # Not a constant, but a client cannot read the environment and needs to know which
    # person this installation is configured for.
    exported["today"] = local_today().isoformat()
    exported["configured_subject"] = get_settings().subject
    return exported
