"""What a conclusion is called, in the words the person is sent.

This lived in the dashboard, and `service/episodes.py` imported it from there to write the
message a person receives on Telegram. A service reaching up into a screen for the words it
sends is backwards: the phone and the dashboard are two clients of this system, and the
words the system says about a conclusion belong to the system.

Only what a notification needs is here. Everything a screen says about itself stays in the
screen, where the user decided it should live.
"""

from wha.models import Disposition

# The label a person sees, and one sentence saying what it means.
#
# "Nothing points towards illness" read "Probably nothing to worry about" until 5 September
# 2026, and "nothing to worry about" is on the `never_say` list in red_flags.yaml. The
# phrase filter runs on what the model writes, not on the words the system ships, so the
# system was breaking its own safety rule in a string it had written by hand.
DISPOSITION_PHRASES: dict[str, tuple[str, str]] = {
    Disposition.LIKELY_ILLNESS.value: (
        "Possibly coming down with something",
        (
            "Your answers and your overnight readings together point towards an infection "
            "more than to anything else. This is not a diagnosis."
        ),
    ),
    Disposition.LIKELY_BENIGN.value: (
        "Nothing points towards illness",
        "Nothing here points towards illness. Keep an eye on how you feel.",
    ),
    Disposition.EXPLAINED_BY_EVENT.value: (
        "Explained by something you did",
        (
            "Something specific accounts for it, such as a hard workout, a drink, a "
            "vaccination or a flight."
        ),
    ),
    Disposition.ESCALATED.value: (
        "Get medical help now",
        "You described something that needs assessing by a person, not an app.",
    ),
    Disposition.UNRESOLVED.value: (
        "Could not tell",
        (
            "There was not enough to separate the possible causes, and asking more was not "
            "worth interrupting you again."
        ),
    ),
    Disposition.INSUFFICIENT_DATA.value: (
        "Still learning your normal",
        (
            "A few more nights of wear are needed before any reading can be judged against "
            "your own baseline."
        ),
    ),
}

_FALLBACK = ("Concluded", "")


def disposition_phrase(value: object) -> tuple[str, str]:
    """The label and the sentence for a disposition. Never raises on an unknown value."""
    key = getattr(value, "value", value)
    return DISPOSITION_PHRASES.get(str(key), _FALLBACK)


def disposition_message(value: object, note: str | None = None) -> str:
    """The full message a person is sent when an investigation closes.

    Label, then what it means, then the care-pathway lines. The last part is not optional:
    `red_flags.yaml` sets `always_include_escalation_criteria: true` and its own note
    explains why a BENIGN conclusion needs it most, being the one somebody is most likely
    to act on by doing nothing.

    Built here because the two time-based closes in `episode_lifecycle` never reach the
    agent's conclude node, and so used to send nothing at all.
    """
    label, meaning = disposition_phrase(value)
    # `note` replaces the stock meaning where the stock meaning would be FALSE. UNRESOLVED
    # normally says asking more was not worth interrupting you, which is accurate when the
    # policy decided that and is a lie when the investigation simply ran out of nights.
    # Telling somebody the wrong reason for stopping is its own harm.
    lines = [f"Your investigation has closed: {label}.", note or meaning]
    try:
        from wha.safety.rules import load_red_flags

        lines.extend(load_red_flags().outcome_guidance.default)
    except Exception:  # noqa: BLE001, S110
        # The knowledge file failing to load must not stop the person being told their
        # investigation ended. The criteria are omitted rather than invented.
        pass
    return "\n\n".join(line for line in lines if line)


def symptom_label(flag_id: str) -> str:
    """A symptom rule id in the words a person would use.

    Read from `red_flags.yaml` rather than held in a dictionary here, so a symptom added
    to the knowledge file cannot appear on a screen as `rf_poor_intake`. Tracked symptoms
    carry an explicit label; tier A and tier B rules do not, so their first match phrase
    is used, which is written in ordinary words already because it has to match what
    somebody types.
    """
    try:
        from wha.safety.rules import load_red_flags

        config = load_red_flags()
        for rule in config.tracked:
            if rule.id == flag_id:
                return rule.label
        for rule in [*config.tier_a, *config.tier_b]:
            if rule.id == flag_id and rule.match:
                return rule.match[0]
    except Exception:  # noqa: BLE001, S110
        pass
    # Never the raw id on a screen. Stripping the prefix leaves something readable.
    return flag_id.removeprefix("rf_").removeprefix("sx_").replace("_", " ")
