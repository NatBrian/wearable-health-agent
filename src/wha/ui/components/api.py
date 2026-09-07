"""The one way a screen reaches the application: over HTTP, like any other client.

Screens used to import service functions directly. That was already a clean layering, with
no SQL and no database access in any view, but only Python could cross it, so replacing
Streamlit meant writing a backend first. Everything now goes through the HTTP client.

This module is deliberately thin. It holds the client, the cached config, and the one
message a screen shows when the application cannot be reached, which must never look like
"you have no data".
"""

from typing import Any

import streamlit as st

from wha.api.client import ApiClient, ApiUnavailable, get_client


def api() -> ApiClient:
    """The shared HTTP client."""
    return get_client()


@st.cache_data(ttl=60)
def config() -> dict[str, Any]:
    """Thresholds and today's date, from the application rather than from an import.

    Cached briefly: these change when settings change, not between page renders.
    """
    return api().config()


def today() -> Any:
    """The subject's local date, decided by the application, not by the browser."""
    from datetime import date

    return date.fromisoformat(config()["today"])


def unavailable(exc: ApiUnavailable) -> None:
    """Say the application is unreachable, and never imply the person has no data.

    A dashboard that renders empty when the backend is down looks identical to one
    reporting a healthy person with nothing recorded. In a health system those two must
    never look the same.
    """
    st.error(
        "**Cannot reach the application.** This screen is showing nothing because the "
        "connection failed, not because there is nothing to show. Nothing here is a "
        "statement about your health."
    )
    st.caption(str(exc))
