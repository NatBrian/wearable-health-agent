"""What this person's device provides, what we store, and what reaches the decision.

Three different questions get confused with each other:

1. What does **Health Connect** define? Around sixty record types, nine of them vitals.
2. What does **this person's watch actually populate**? Far fewer, and it differs between
   people depending on the device, the firmware and which features they have switched on.
3. What does **the decision** use? Fewer still, because a channel can only move the belief
   if ``causes.yaml`` carries a cited likelihood relating it to one of the twelve causes.

The ingestion layer stores the raw payload verbatim before parsing anything, so nothing a
device sends is ever lost. But the normaliser recognises a fixed set of keys, and until
now a payload containing heart rate variability, respiratory rate or skin temperature
would have been stored and then silently ignored. Someone whose watch records more than
the developer's would get no benefit from it and no notice that it was happening.

This module exists to make that visible rather than silent.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChannelStatus:
    """One data channel, and how far through the system it gets."""

    payload_key: str
    label: str
    reaches_decision: bool
    note: str


# Keys the normaliser parses, and how far each one travels.
#
# "Reaches the decision" means the value can change what the system concludes. A channel
# is stored and shown to the agent either way, but it can only move the belief if
# causes.yaml relates it to a cause, and writing such a relation is a clinical judgement
# rather than a coding one.
RECOGNISED_CHANNELS: tuple[ChannelStatus, ...] = (
    ChannelStatus(
        "heart_rate",
        "Heart rate",
        True,
        "The overnight resting rate derived from this is what the whole system watches.",
    ),
    ChannelStatus(
        "steps",
        "Steps",
        True,
        "Used to judge how active the previous day was.",
    ),
    ChannelStatus(
        "sleep",
        "Sleep stages",
        True,
        "Short sleep raises heart rate, so it is subtracted before judging a night.",
    ),
    ChannelStatus(
        "exercise",
        "Workouts",
        True,
        "A late workout raises overnight heart rate and is subtracted before judging.",
    ),
    ChannelStatus(
        "oxygen_saturation",
        "Blood oxygen",
        False,
        "Stored and shown, but causes.yaml has no likelihood for it, so it cannot move "
        "the conclusion. See docs/DISCLOSURES.md.",
    ),
    ChannelStatus(
        "distance",
        "Distance",
        False,
        "Activity context for the agent to read. Steps already carry the same signal.",
    ),
    ChannelStatus(
        "total_calories",
        "Energy burned",
        False,
        "Activity context for the agent to read.",
    ),
)

RECOGNISED_KEYS = frozenset(c.payload_key for c in RECOGNISED_CHANNELS)

# Payload keys that are structure rather than health data.
_NON_DATA_KEYS = frozenset({"app_version", "timestamp"})

# Health Connect defines these and a device may populate them. None is parsed today.
# The first three are the channels the research corpus identifies as the strongest
# published feature set for illness detection, which is why their absence matters more
# than the length of this list suggests.
UNSUPPORTED_HEALTH_CONNECT_CHANNELS: dict[str, str] = {
    "heart_rate_variability": "Heart rate variability, which falls before symptoms appear",
    "respiratory_rate": "Breathing rate, which rises during infection",
    "skin_temperature": "Skin temperature, which rises during infection",
    "resting_heart_rate": "The device's own resting heart rate, rather than ours",
    "body_temperature": "Body temperature, if measured with a thermometer",
    "blood_pressure": "Blood pressure",
    "hydration": "Fluid intake",
    "weight": "Body weight",
}


@dataclass(frozen=True)
class CapabilityReport:
    """What arrived, what we do with it, and what we are missing."""

    provided: list[str] = field(default_factory=list)
    used_in_decision: list[str] = field(default_factory=list)
    stored_only: list[str] = field(default_factory=list)
    unrecognised: list[str] = field(default_factory=list)
    absent_but_supported: list[str] = field(default_factory=list)

    @property
    def has_unused_data(self) -> bool:
        """True when the device is sending something the decision does not use."""
        return bool(self.stored_only or self.unrecognised)


def describe_payload(body: dict[str, Any]) -> CapabilityReport:
    """Report how far each channel in a payload travels through the system.

    ``unrecognised`` is the important one. It names data the device is sending that the
    normaliser does not parse, which is invisible without this.
    """
    provided = sorted(
        key
        for key, value in body.items()
        if key not in _NON_DATA_KEYS and isinstance(value, list) and value
    )

    by_key = {c.payload_key: c for c in RECOGNISED_CHANNELS}

    used = [k for k in provided if k in by_key and by_key[k].reaches_decision]
    stored_only = [k for k in provided if k in by_key and not by_key[k].reaches_decision]
    unrecognised = [k for k in provided if k not in RECOGNISED_KEYS]
    absent = sorted(k for k in UNSUPPORTED_HEALTH_CONNECT_CHANNELS if k not in provided)

    return CapabilityReport(
        provided=provided,
        used_in_decision=used,
        stored_only=stored_only,
        unrecognised=unrecognised,
        absent_but_supported=absent,
    )


def format_report(report: CapabilityReport) -> str:
    """Render a capability report as plain text for the CLI."""
    lines: list[str] = []
    by_key = {c.payload_key: c for c in RECOGNISED_CHANNELS}

    lines.append("What your watch is sending")
    if not report.provided:
        lines.append("  nothing yet")
    for key in report.provided:
        channel = by_key.get(key)
        if channel is None:
            lines.append(f"  {key:22s} NOT PARSED, stored in the raw record only")
        elif channel.reaches_decision:
            lines.append(f"  {key:22s} used to decide")
        else:
            lines.append(f"  {key:22s} stored and shown, does not affect the decision")

    if report.unrecognised:
        lines.append("")
        lines.append("Sending data this build does not parse")
        for key in report.unrecognised:
            hint = UNSUPPORTED_HEALTH_CONNECT_CHANNELS.get(key, "not yet supported")
            lines.append(f"  {key:22s} {hint}")
        lines.append("  The raw payload is kept, so nothing is lost and these can be")
        lines.append("  added later without re-collecting anything.")

    lines.append("")
    lines.append("Not arriving, though Health Connect defines it")
    for key in report.absent_but_supported:
        lines.append(f"  {key:22s} {UNSUPPORTED_HEALTH_CONNECT_CHANNELS[key]}")
    lines.append("  These are not excluded by choice. The bridge app supports them and")
    lines.append("  Health Connect defines them, so a channel is absent for one of three")
    lines.append("  reasons: your watch does not record it, the feature is switched off,")
    lines.append("  or the app was never granted permission to read it. Only the last is")
    lines.append("  checkable here: open Health Connect, App permissions, and confirm")
    lines.append("  every type is allowed.")

    return "\n".join(lines)
