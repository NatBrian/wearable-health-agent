"""The days the demo film walks through, and what each one is predicted to do.

Every day carries an `expect` block written BEFORE the day is run. That is the whole point
of this file. A simulation you watch and then describe afterwards will always look like it
worked, because you write the description to fit what you saw. A simulation that states its
prediction first can fail, and this project's history says it will: fifteen defects have
been found by using the product and none of them by reading it.

`build.py` halts on the first day whose outcome does not match its prediction. A mismatch
is not something to adjust the prediction for. It is either a defect in the system or a
misunderstanding of the system, and both need finding before a camera is pointed at it.

ONE DISTINCTION MATTERS HERE, and it is the difference between a prediction and a fit.

The fields about the SYSTEM are predicted from its documented rules and never adjusted:
whether a night flags, whether an investigation opens, whether the agent asks, whether the
safety floor escalates, which symptoms reach the timeline. Those are the claims the film
makes, and if one of them fails the system is wrong or the film is wrong.

`level` is different. It is a property of the SIMULATOR, not of the system: the amplitude
injected is not the residual delivered, because the generator rounds every minute to a
whole bpm and each cause has a decay profile that the nocturnal window only partly
catches. The exertion preset injects 2.91 bpm and delivers 0.59. So `level` is MEASURED
first with `--stage levels`, which runs the real ingest and scoring path with no agent and
no model, and then written down. Predicting it from the amplitude would be guessing, and
guessing that happened to be right would teach nothing.

The first build of this timeline injected an illness event on every red night, which
stacked into residuals of +5.5, +10.5 and +15.0 bpm. The measured effect of infection on
resting heart rate in this project's own cohort work is 1.60 bpm. There is one illness
event per illness now, and one relapse.

Dates are chosen so the story begins the day after the real watch data ends.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Subject `me` was worn from 31 August. Everything before that has no nocturnal coverage,
# so 27 prologue nights are generated at the resting rate measured from the real ones,
# purely to get the baseline off the SHRINKING rung and onto MATURE, which needs 28 usable
# nights. Nothing in the film happens here.
PROLOGUE_START = date(2026, 8, 4)
PROLOGUE_END = date(2026, 8, 30)

# The real nights, copied out of `me` as raw readings and rescored by the real nightly job.
REAL_START = date(2026, 8, 31)
REAL_END = date(2026, 9, 6)

# The person's own resting rate, measured from those seven nights: 44, 45, 45, 47, 47, 45,
# 46. The prologue is generated at this rate so the baseline is continuous with the real
# data rather than stepping when the real nights begin.
BASE_BPM = 45.5
SEED = 7


@dataclass(frozen=True)
class Expect:
    """What this day should produce. Written before the day is run.

    Every field is optional. `None` means "not asserted", which is honest: a prediction
    should only cover what is actually predictable, and padding it with guesses would turn
    the halt condition into noise.
    """

    level: str | None = None
    """GREEN, YELLOW, RED or NA, from the detections table."""

    flagged: bool | None = None
    """Whether the night flagged. Asserted where the level deliberately is not."""

    episode_open: bool | None = None
    """Whether an investigation is open at the end of the day."""

    episode_is_new: bool = False
    """Whether a NEW investigation opened today, as opposed to one carrying on."""

    question_asked: bool | None = None
    """Whether the agent put a question to the person today."""

    escalation: str | None = None
    """The urgency band the safety floor produced, if any."""

    symptoms_on_timeline: tuple[str, ...] = ()
    """Flag ids that must be on the symptom timeline by the end of the day."""

    disposition: str | None = None
    """The episode's disposition, once it closes."""

    note: str = ""
    """Why this day is in the film at all. Read this before changing anything."""


@dataclass(frozen=True)
class Day:
    date: date
    scenario: str
    expect: Expect
    events: tuple[dict[str, object], ...] = ()
    """Extra causes scheduled on this night, for elevations the agent has to explain."""

    tell: tuple[str, ...] = ()
    """What the person volunteers, unprompted, through `wha tell`."""

    answer: str | None = None
    """What the person replies if a question is waiting for them."""

    review: tuple[str, str] | None = None
    """(decision, rationale) if a drafted conclusion is waiting to be reviewed.

    The four the system accepts are approve, reject, edit and escalate. Leaving this
    unset is not neutral: the draft is RELEASED unreviewed once the window passes, and
    recorded as "not approved". That is the correct default, and it is why the first
    build closed an investigation on a day nobody expected. Silence is a decision here
    too.
    """

    chapter: str = ""


DAYS: tuple[Day, ...] = (
    Day(
        date=date(2026, 9, 7),
        scenario="healthy",
        chapter="7. Four quiet nights",
        expect=Expect(
            level="GREEN",
            flagged=False,
            episode_open=False,
            question_asked=False,
            note="An ordinary night. The system's normal state is silence, and the film "
            "has to establish that before any alarm means anything.",
        ),
    ),
    Day(
        date=date(2026, 9, 8),
        scenario="healthy",
        events=({"kind": "exercise", "amplitude_bpm": 4.41, "end_offset_h": 1.5},),
        chapter="7. Four quiet nights",
        expect=Expect(
            level="GREEN",
            flagged=False,
            episode_open=False,
            question_asked=False,
            note="Hard training late in the evening. 4.41 bpm is one standard deviation "
            "above the mean for exertion in causes.yaml (2.91, sd 1.50), a heavy session "
            "rather than an invented number. It lands at +1.59, well inside normal, which "
            "is itself worth showing: a hard session does not look like an illness here.",
        ),
    ),
    Day(
        date=date(2026, 9, 9),
        scenario="healthy",
        events=({"kind": "alcohol", "amplitude_bpm": 3.70},),
        chapter="7. Four quiet nights",
        expect=Expect(
            level="YELLOW",
            flagged=False,
            episode_open=False,
            question_asked=False,
            note="Alcohol, at one standard deviation above the mean in causes.yaml (2.60, "
            "sd 1.10). Lands at +3.50, which is YELLOW. Yellow does not flag, and adding a "
            "yellow-persistence arm was measured across 738 person-weeks and caught zero "
            "extra cases. This is the film's evidence that the quiet is chosen, not luck.",
        ),
    ),
    Day(
        date=date(2026, 9, 10),
        scenario="healthy",
        chapter="7. Four quiet nights",
        expect=Expect(level="GREEN", flagged=False, episode_open=False, question_asked=False),
    ),
    Day(
        date=date(2026, 9, 11),
        scenario="healthy",
        chapter="7. Four quiet nights",
        expect=Expect(level="GREEN", flagged=False, episode_open=False, question_asked=False),
    ),
    Day(
        date=date(2026, 9, 12),
        scenario="illness",
        chapter="8. First red night, still silent",
        tell=("I feel a bit dizzy today",),
        expect=Expect(
            level="RED",
            flagged=False,
            episode_open=False,
            question_asked=False,
            symptoms_on_timeline=("sx_dizziness",),
            note="Onset. One RED night is not an alert: flagging needs two consecutive, "
            "the published NightSignal rule. So the person volunteers a symptom into a "
            "system that has not asked them anything. Dizziness is TRACKED, not a red "
            "flag: recorded, and it escalates on nothing, because tracking asserts no "
            "clinical threshold while an invented persistence figure would. This recorded "
            "symptom is what blocks the false close on the 16th.",
        ),
    ),
    Day(
        date=date(2026, 9, 13),
        scenario="healthy",
        chapter="10. The agent wakes",
        answer="I have had a fever since last night, and chills",
        expect=Expect(
            level="RED",
            flagged=True,
            episode_open=True,
            episode_is_new=True,
            question_asked=True,
            symptoms_on_timeline=("sx_dizziness", "rf_fever"),
            note="Second consecutive RED, on the tail of the same illness. The "
            "investigation opens and the agent runs for the first time in the film. It "
            "asks one question, and it asks because the arithmetic said the answer was "
            "worth the interruption. Fever alone is one Tier B flag on one night, so it is "
            "recorded and does not escalate yet.",
        ),
    ),
    Day(
        date=date(2026, 9, 14),
        scenario="healthy",
        chapter="13. Two symptoms across two nights",
        tell=("I have been vomiting since this morning and cannot keep water down",),
        expect=Expect(
            level="RED",
            flagged=True,
            episode_open=True,
            symptoms_on_timeline=("sx_dizziness", "rf_fever", "rf_persistent_vomiting"),
            escalation="same_day",
            note="THE CHAPTER THIS FILM EXISTS FOR. Fever on the 13th and vomiting on the "
            "14th are two Tier B flags. Until 7 September 2026 co-occurrence meant 'in the "
            "same message', so these counted as two unrelated singletons and the system "
            "said nothing. Now the timeline is read across nights and the floor escalates "
            "to same-day care. If this day does not escalate, stop and find out why.",
        ),
    ),
    Day(
        date=date(2026, 9, 15),
        scenario="healthy",
        chapter="15. Feeling better, and it does not close",
        tell=("I feel a lot better today, the fever has gone",),
        expect=Expect(
            level="YELLOW",
            episode_open=True,
            note="The number is coming down and the person says the fever has broken. The "
            "investigation stays OPEN. In dengue the critical phase BEGINS at "
            "defervescence, which is to say the most dangerous hours start when the "
            "patient first feels better.",
        ),
    ),
    Day(
        date=date(2026, 9, 16),
        scenario="healthy",
        chapter="15. A green night, and it still does not close",
        expect=Expect(
            level="GREEN",
            flagged=False,
            episode_open=True,
            note="THE OTHER CHAPTER THIS FILM EXISTS FOR. A fully green night, the person "
            "already said they feel better, and the investigation still does not close. "
            "Faget's sign puts relative bradycardia in dengue, typhoid, Legionella and Q "
            "fever, and Radin measured resting heart rate taking about 79 days to return "
            "to baseline after COVID. A green run is evidence about the READING, not about "
            "the PERSON, and a benign close is blocked while a symptom is outstanding.",
        ),
    ),
    Day(
        date=date(2026, 9, 17),
        scenario="healthy",
        events=({"kind": "illness", "amplitude_bpm": 5.4},),
        chapter="16. It comes back, and the person rejects the conclusion",
        tell=("the fever is back and I feel worse than before",),
        review=(
            "reject",
            "I am not better. The fever came back today and I feel worse than I did before.",
        ),
        expect=Expect(
            level="RED",
            flagged=False,
            episode_open=True,
            episode_is_new=True,
            note="The relapse, at +6.0 bpm. It does not flag on its own night, because the "
            "16th was green and flagging needs two consecutive reds. It arrives inside the "
            "seven day window that separates one "
            "illness from the next, so it belongs to the SAME investigation rather than "
            "opening a fresh one. Saddleback dengue is the concrete case: the second peak "
            "arrives one to two days after the fever breaks and is the dangerous one.\n\n"
            "AND THE HUMAN CHECKPOINT. On the 16th, the green night, the agent drafted a "
            "conclusion and paused to have it checked. The person reads it on the 17th and "
            "REJECTS it, because the thing it concluded about is happening again. This is "
            "the oversight step doing the one job it exists for, and the film gets to show "
            "a person overruling the system rather than rubber stamping it. Left alone, "
            "the draft is released after 36 hours and recorded as not approved, which is "
            "what happened on the first build and is why the investigation closed on a day "
            "nobody expected.\n\n"
            "PREDICTED WRONG THE FIRST TIME, and the harness caught it. This said the "
            "relapse would continue the SAME investigation. It does not, and the reason is "
            "better than the prediction: rejecting a conclusion closes that investigation "
            "as UNRESOLVED, which is explicitly not an all clear, and the continuing "
            "illness opens a new one that is LINKED to it by preceded_by_episode_id. "
            "Nothing about the illness is lost, the record shows a person overruling the "
            "system, and the reject is visibly not treated as reassurance.",
        ),
    ),
    Day(
        date=date(2026, 9, 18),
        scenario="healthy",
        chapter="16. The person raises the urgency, not the AI",
        review=(
            "escalate",
            "I am worse today, not better. I want this treated as urgent.",
        ),
        expect=Expect(
            level="RED",
            flagged=True,
            note="The linked investigation drafted its own conclusion the moment it "
            "opened, because it already knew about the fever, the vomiting and the poor "
            "intake, and asking again would have added nothing. The person reads that "
            "draft and ESCALATES it. This is the direction of override that matters: a "
            "human can always raise the urgency, and neither the model nor the person can "
            "lower what the deterministic floor has already decided.",
        ),
    ),
    Day(
        date=date(2026, 9, 19),
        scenario="healthy",
        chapter="16. Recovery begins",
        expect=Expect(
            level="RED",
            flagged=True,
            note="Still raised, and the escalation from yesterday closed that "
            "investigation. Whether a further one opens is left unasserted: it depends on "
            "the detector, and predicting it either way would be a guess dressed as a "
            "claim.",
        ),
    ),
    Day(
        date=date(2026, 9, 20),
        scenario="healthy",
        chapter="16. A close that speaks",
        tell=("I am completely better now, no fever and eating normally",),
        expect=Expect(
            level="YELLOW",
            note="Symptoms retracted, so the investigation may close. The close must SAY "
            "something. A time-based close used to be silent, which meant a person learned "
            "nothing from an investigation that had run for over a week. Silence after a "
            "warning reads as an all clear, which is the opposite of what it meant.",
        ),
    ),
    Day(
        date=date(2026, 9, 21),
        scenario="healthy",
        chapter="16. The first quiet night",
        answer="I feel completely fine now. No fever, no dizziness, eating and drinking normally.",
        expect=Expect(
            level="GREEN",
            flagged=False,
            note="One green night is not enough to close on, and that is the same rule in "
            "the other direction: a benign close needs two consecutive green nights, so "
            "the earliest this can end is tomorrow. Predicted the investigation would "
            "already be closed here and it was not, because the 20th was amber.",
        ),
    ),
    Day(
        date=date(2026, 9, 22),
        scenario="healthy",
        chapter="16. A close that speaks",
        review=("approve", "Yes, that is what happened. I am well again."),
        expect=Expect(
            level="GREEN",
            flagged=False,
            episode_open=False,
            note="The third and last review decision, and the only APPROVE in the film. "
            "Left alone this one was released unreviewed and closed anyway, correctly and "
            "recorded as not approved, which is a weaker ending than a person reading the "
            "conclusion about their own illness and agreeing with it.\n\n"
            "Two consecutive green nights, no symptom outstanding, nothing waiting on "
            "the person. Now it may close, and the close has to SAY something. A "
            "time-based close used to be silent, so a person learned nothing from an "
            "investigation that had run for over a week, and silence after a warning reads "
            "as an all clear.",
        ),
    ),
    Day(
        date=date(2026, 9, 23),
        scenario="healthy",
        chapter="17. Chest pain",
        expect=Expect(
            level="GREEN",
            flagged=False,
            episode_open=False,
            question_asked=False,
            note="Filmed live rather than built here, because the five Marburg items have "
            "to be elicited in conversation and that conversation IS the scene. The build "
            "only has to leave the system quiet and closed, so that what happens next is "
            "unambiguously the result of what the person types.",
        ),
    ),
)


def day_for(when: date) -> Day | None:
    return next((d for d in DAYS if d.date == when), None)


def story_start() -> date:
    return DAYS[0].date


def story_end() -> date:
    return DAYS[-1].date
