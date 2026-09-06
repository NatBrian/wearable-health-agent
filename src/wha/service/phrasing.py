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
