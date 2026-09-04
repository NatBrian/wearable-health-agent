"""Plain-English wording for everything the dashboard shows a person.

The interface spoke in the vocabulary of the code: dispositions, residuals, rungs,
Bayesian differentials, episode ids. Those are the right names inside the system and the
wrong ones in front of a person who wants to know whether they are getting ill.

Every user-facing string that names an internal concept comes from here, so the same
idea is never called two different things on two different pages. The technical name
stays available beside the plain one wherever a reader might want to check the
machinery, which is what `technical` is for.
"""

from wha.models import BaselineRung, DetectionLevel, Disposition, EpisodeState


class Phrase:
    """A plain-English label, a short explanation, and the internal name behind it."""

    __slots__ = ("explanation", "label", "technical")

    def __init__(self, label: str, explanation: str, technical: str) -> None:
        self.label = label
        self.explanation = explanation
        self.technical = technical


LEVEL_PHRASES: dict[str, Phrase] = {
    DetectionLevel.GREEN.value: Phrase(
        "Normal",
        "Your overnight heart rate was in your usual range.",
        "GREEN",
    ),
    DetectionLevel.YELLOW.value: Phrase(
        "Slightly raised",
        "A little above your usual range. On its own this is not unusual.",
        "YELLOW",
    ),
    DetectionLevel.RED.value: Phrase(
        "Clearly raised",
        "Well above your usual range for this time of night.",
        "RED",
    ),
    DetectionLevel.NA.value: Phrase(
        "Not enough data",
        "Your watch was not worn long enough overnight to measure this.",
        "NA",
    ),
}


DISPOSITION_PHRASES: dict[str, Phrase] = {
    Disposition.LIKELY_ILLNESS.value: Phrase(
        "Possibly coming down with something",
        "Your answers and your overnight readings together point towards an infection "
        "more than to anything else. This is not a diagnosis.",
        "LIKELY_ILLNESS",
    ),
    Disposition.LIKELY_BENIGN.value: Phrase(
        # This read "Probably nothing to worry about", and "nothing to worry about" is on
        # the `never_say` list in red_flags.yaml. The phrase filter runs on what the MODEL
        # writes and not on the interface's own words, so the system was breaking its own
        # safety rule in a string it shipped. See test_no_interface_phrase_is_on_never_say.
        "Nothing points towards illness",
        "Nothing here points towards illness. Keep an eye on how you feel.",
        "LIKELY_BENIGN",
    ),
    Disposition.EXPLAINED_BY_EVENT.value: Phrase(
        "Explained by something you did",
        "Something specific accounts for it, such as a hard workout, a drink, "
        "a vaccination or a flight.",
        "EXPLAINED_BY_EVENT",
    ),
    Disposition.ESCALATED.value: Phrase(
        "Get medical help now",
        "You described something that needs assessing by a person, not an app.",
        "ESCALATED",
    ),
    Disposition.UNRESOLVED.value: Phrase(
        "Could not tell",
        "There was not enough to separate the possible causes, and asking more was not "
        "worth interrupting you again.",
        "UNRESOLVED",
    ),
    Disposition.INSUFFICIENT_DATA.value: Phrase(
        "Still learning your normal",
        "A few more nights of wear are needed before any reading can be judged against "
        "your own baseline.",
        "INSUFFICIENT_DATA",
    ),
}


EPISODE_STATE_PHRASES: dict[str, Phrase] = {
    EpisodeState.OPEN.value: Phrase(
        "Looking into it",
        "Gathering information about a raised reading.",
        "OPEN",
    ),
    EpisodeState.AWAITING_USER.value: Phrase(
        "Waiting on your answer",
        "There is a question for you.",
        "AWAITING_USER",
    ),
    EpisodeState.AWAITING_MEASUREMENT.value: Phrase(
        "Waiting on a reading",
        "You have been asked to take a measurement or wear the watch tonight.",
        "AWAITING_MEASUREMENT",
    ),
    EpisodeState.AWAITING_HUMAN_REVIEW.value: Phrase(
        "Waiting on review",
        "A summary has been drafted and is waiting to be checked.",
        "AWAITING_HUMAN_REVIEW",
    ),
    EpisodeState.CLOSED.value: Phrase(
        "Finished",
        "This one is done.",
        "CLOSED",
    ),
}


RUNG_PHRASES: dict[str, Phrase] = {
    BaselineRung.COLD.value: Phrase(
        "Just started",
        "Not enough nights yet to know your normal, so nothing is judged against it.",
        "COLD",
    ),
    BaselineRung.PRIOR_DOMINATED.value: Phrase(
        "Learning",
        "Only a few nights so far, so readings are compared mostly against typical adults.",
        "PRIOR_DOMINATED",
    ),
    BaselineRung.SHRINKING.value: Phrase(
        "Getting to know you",
        "Enough nights to start using your own pattern alongside typical adults.",
        "SHRINKING",
    ),
    BaselineRung.PERSONAL.value: Phrase(
        "Using your own pattern",
        "Mostly judged against your own history now.",
        "PERSONAL",
    ),
    BaselineRung.MATURE.value: Phrase(
        "Well established",
        "Four weeks or more of your own nights. Comparisons are against you alone.",
        "MATURE",
    ),
}


_FALLBACK = Phrase("Unknown", "", "")


def _lookup(table: dict[str, Phrase], value: object) -> Phrase:
    """Resolve an enum or string to its phrase, never raising on an unexpected value."""
    key = getattr(value, "value", value)
    return table.get(str(key), _FALLBACK)


# Below this rung the shrinkage estimate is still dominated by the population prior, so
# "your usual range" is not yet a statement about this person.
_PERSONAL_RUNGS = {"SHRINKING", "PERSONAL", "MATURE"}


def level_phrase(value: object, rung: object = None) -> Phrase:
    """Plain wording for a nightly detection level.

    Every phrase said "your usual range" regardless of how much the system knew about the
    person. On a three-night baseline that range is the population prior, and the Today
    page said "in your usual range" directly beneath a tile reading "baseline: Learning".
    When the baseline has not shrunk toward the subject yet, the wording says what the
    comparison actually is rather than claiming a personal normal it has not learned.
    """
    phrase = _lookup(LEVEL_PHRASES, value)
    if rung is None:
        return phrase

    rung_name = getattr(rung, "value", None) or getattr(rung, "name", None) or str(rung)
    if rung_name in _PERSONAL_RUNGS or phrase.technical == "NA":
        return phrase

    return Phrase(
        phrase.label,
        phrase.explanation.replace("your usual range", "the usual range for an adult").rstrip(".")
        + ". Your own range is still being learned, so this is measured against a typical "
        "adult rather than against you.",
        phrase.technical,
    )


def disposition_phrase(value: object) -> Phrase:
    """Plain wording for what an investigation concluded."""
    return _lookup(DISPOSITION_PHRASES, value)


def episode_state_phrase(value: object) -> Phrase:
    """Plain wording for where an investigation has got to."""
    return _lookup(EPISODE_STATE_PHRASES, value)


def rung_phrase(value: object) -> Phrase:
    """Plain wording for how well the system knows this person's normal."""
    return _lookup(RUNG_PHRASES, value)


def describe_bpm_difference(value: float | None) -> str:
    """Describe a heart rate difference in words rather than a signed number.

    "+3.2 bpm" tells a reader nothing about whether that is a lot.
    """
    if value is None:
        return "not measured"
    if value >= 4.0:
        return f"{value:.1f} bpm above your usual, which is a clear rise"
    if value >= 3.0:
        return f"{value:.1f} bpm above your usual, which is a slight rise"
    if value >= 0:
        return f"{value:.1f} bpm above your usual, which is within normal variation"
    return f"{abs(value):.1f} bpm below your usual"


def episode_reference(episode_id: str, opened_on: object) -> str:
    """A human reference for an investigation, rather than its database id."""
    return f"Investigation opened {opened_on}"
