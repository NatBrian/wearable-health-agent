"""The numbers quoted in the documentation must match the running system.

Prose figures drift. The README claimed a 240-minute coverage gate against an actual 180,
a 48-hour staleness limit against an actual 72, and a population prior of 62.0 and 7.5
against 62.75 and 8.64. The audit dashboard page had drifted the same way before it was
rewritten to read its figures from the constants.

A reader cannot tell a stale number from a current one, so the difference between "roughly
right" and "wrong" is invisible to them. These tests make it visible here instead.
"""

from pathlib import Path

from wha.constants import (
    DETECT_PERSISTENCE_NIGHTS,
    DETECT_RED_BPM,
    DETECT_YELLOW_BPM,
    INGEST_STALE_REFUSE_HOURS,
    MIN_NOCTURNAL_MINUTES,
    N_CAUSES,
    POP_PRIOR_RHR_MEAN_BPM,
    POP_PRIOR_RHR_SD_BPM,
)

README = Path("README.md")
CHANNELS_DOC = Path("docs/DESIGN-DATA-CHANNELS.md")


def test_readme_quotes_the_real_quality_gates() -> None:
    """Coverage minimum and staleness limit, as actually enforced."""
    text = README.read_text(encoding="utf-8")

    assert f"{MIN_NOCTURNAL_MINUTES}\\text{{ minutes}}" in text
    assert f"older than {INGEST_STALE_REFUSE_HOURS} hours" in text


def test_readme_quotes_the_real_population_prior() -> None:
    """The prior the baseline shrinks toward, from Bloomfield et al. 2024."""
    text = README.read_text(encoding="utf-8")

    assert str(POP_PRIOR_RHR_MEAN_BPM) in text
    assert str(POP_PRIOR_RHR_SD_BPM) in text


def test_readme_quotes_the_real_state_count() -> None:
    """Twelve causes enumerated exactly."""
    text = README.read_text(encoding="utf-8")

    assert f"2^{{{N_CAUSES}}} = 4,096" in text or f"{2**N_CAUSES:,}" in text


def test_channels_doc_quotes_the_real_detection_thresholds() -> None:
    """The design note explains the thresholds, so it must state them correctly."""
    text = CHANNELS_DOC.read_text(encoding="utf-8")

    assert f"{DETECT_YELLOW_BPM} and {DETECT_RED_BPM} bpm" in text


def test_channels_doc_describes_every_channel_the_normaliser_parses() -> None:
    """The table of channels must not omit one the system actually ingests."""
    from wha.ingest.capability import RECOGNISED_CHANNELS

    text = CHANNELS_DOC.read_text(encoding="utf-8").lower()

    for channel in RECOGNISED_CHANNELS:
        assert channel.label.lower() in text, (
            f"'{channel.label}' is parsed but the design note does not mention it"
        )


def test_persistence_rule_is_stated_correctly() -> None:
    """How many raised nights it takes before anything opens."""
    text = CHANNELS_DOC.read_text(encoding="utf-8")
    assert DETECT_PERSISTENCE_NIGHTS == 2, (
        "The design note says a single raised night is not enough. Update it if this changes."
    )
    assert "one well-chosen question" in text
