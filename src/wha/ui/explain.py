"""Every explanatory sentence the dashboard says, in one place.

Two rules, both enforced by tests rather than by care:

* **No copy here contains a figure.** Not a threshold, not a night count, not a
  percentage. Numbers come from the application over HTTP, because a number typed into a
  screen drifts away from the code that uses it, and this dashboard shipped an explanation
  claiming a coverage minimum of one hundred and twenty minutes against an actual hundred
  and eighty. Words only, here.
* **Nothing here may appear on the `never_say` list in `data/knowledge/red_flags.yaml`.**
  The phrase filter runs on what the model writes. It did not run on the interface's own
  strings, and the Today page shipped "Probably nothing to worry about" as a label while
  "nothing to worry about" sat on that list. `tests/unit/ui/test_wording_never_say.py`
  sweeps every value below.

Keys are stable ids: `step.<step_id>.what`, `step.<step_id>.why`, `level.<LEVEL>`,
`rung.<RUNG>`, `metric.<name>`. A screen asks for a key, never for a sentence.
"""

TEXT: dict[str, str] = {
    # ------------------------------------------------------------------ what this is
    "home.what_it_is": (
        "This watches your resting heart rate while you sleep. When a night is high for "
        "you, it works out what is most likely behind it and decides whether asking you a "
        "question is worth interrupting you for."
    ),
    "home.emergency": (
        "Contact a clinician or emergency services. Do not wait "
        "for this system. It runs once a night, nobody is watching it on your behalf, and "
        "it cannot see how you feel."
    ),
    "home.can": (
        "Notice when your sleeping heart rate is unusual for you, rather than unusual for "
        "people in general. Ask you one short question when your answer would change what "
        "it concludes. Show you every step of how it reached any result, and quote the "
        "source behind every clinical sentence it writes."
    ),
    "home.cannot": (
        "It cannot diagnose anything, and it is not a medical device. It sees your heart "
        "rate, your sleep and what you type, and nothing else. It cannot tell you that you "
        "are well: a normal night means one measurement was normal. It can be wrong in "
        "both directions, and the accuracy it was measured at is published in the record."
    ),
    "home.judging": (
        "Your phone hands over what your watch recorded. The system finds the stretch you "
        "actually slept, takes the middle heart rate across it, and compares that against "
        "your own normal built from your recent nights. If a recorded evening workout "
        "explains part of the rise, that part is subtracted first. Only if the rest is "
        "high enough, on enough nights in a row, does it open an investigation."
    ),
    "home.provenance": (
        "Some clinical figures behind this system come from published studies and some do "
        "not. The ones with no published source are marked as unevidenced wherever they "
        "appear, here and in the record, rather than quietly presented as fact."
    ),
    "home.nav.today": "What happened last night, and anything that needs you.",
    "home.nav.history": "Your nights over time, and what was looked into.",
    "home.nav.audit": "Every step the system took, and proof the record has not changed.",
    "home.nav.settings": "Where readings come from, and how often you get asked.",
    # ------------------------------------------------------------- what a level means
    "level.GREEN": (
        "Your sleeping heart rate was in your usual range. This says the measurement was "
        "ordinary for you. It is not a statement about your health."
    ),
    "level.YELLOW": (
        "Your sleeping heart rate was somewhat above your usual range. On its own this "
        "opens nothing: a single raised night is common and has many ordinary causes."
    ),
    "level.RED": (
        "Your sleeping heart rate was clearly above your usual range. Where this happens "
        "on enough nights in a row, the system opens an investigation and may ask you "
        "about it."
    ),
    # Below the shrinking rung the band is still mostly the population estimate, so "your
    # usual range" is a claim the system has not earned. The Today page once said "in your
    # usual range" directly beneath a tile reading "baseline: Learning".
    "level.immature_note": (
        "Your own range is still being learned, so this night was measured against a "
        "typical adult rather than against you."
    ),
    "level.NA": (
        "Too little of this night was measured to judge it. That is a gap in the data, not "
        "a result."
    ),
    # What the system is doing about it, and what you should do. A colour with no next
    # step reads as a warning nobody will act on: "RED" on its own left a reader asking
    # whether they were ill and what they were supposed to do about it.
    "level.GREEN.next": (
        "Nothing to do. The system will keep watching tonight, and it will contact you if "
        "it ever needs something from you."
    ),
    "level.YELLOW.next": (
        "Nothing to do, and nothing is being looked into. A single raised night is common "
        "and has many ordinary causes: a late drink, a short night, a warm room, a hard "
        "session the day before. A night at this level never opens an investigation, "
        "however many of them there are."
    ),
    "level.RED.next": (
        "Nothing to do right now, and nothing is being looked into yet. One night at this "
        "level is not enough: it takes two clearly raised nights in a row, both of them at "
        "this level, before the system starts looking into it. Single raised nights are "
        "common and have many ordinary causes. If tonight comes out at this level too, it "
        "will open an investigation and may ask you one question."
    ),
    "level.NA.next": (
        "Nothing to do. Too little of the night was measured to judge it, so nothing was "
        "concluded either way."
    ),
    # Does NOT say why the investigation opened, because this string cannot know.
    #
    # It used to say "because your readings were clearly raised on more than one night in
    # a row", which is only one of the three ways an investigation starts: the detector
    # flagging two consecutive nights, the person reporting a symptom, and a recurrence
    # linked to a recent one. Reporting a fever on a green night opened an investigation
    # and this sentence then told the person their readings had been raised, three lines
    # under a heading saying they were in their usual range.
    #
    # Naming the real cause needs the screen to be told which one it was, and it is not.
    # Until it is, saying less is the honest option: everything below is true of all three.
    "level.investigating": (
        "This is being looked into now. It will ask you something if your answer would "
        "change what it concludes, and it will also ask how you are getting on if you "
        "have told it about a symptom and not said it had settled, whether or not the "
        "answer would change anything."
    ),
    "safety.no_local_guidance": (
        "This system has no guidance about any specific illness, including ones that are "
        "common where you live. It knows general health information and it knows your own "
        "readings, and that is all. So it can tell you that a group of symptoms is worth "
        "seeing somebody about, and it cannot tell you which illness they point to, or "
        "warn you about how a particular illness usually behaves. A clinician here can. "
        "This is a deliberate limit rather than an oversight, and it will not change."
    ),
    "safety.what_it_cannot_catch": (
        "What this cannot catch. The rules that raise an alarm on your words match set "
        "phrases, so unusual wording can slip past them. Dizziness and feeling faint raise "
        "no alarm on their own, because nobody has measured how long either should last in "
        "an otherwise well person before it means anything; they are written down and asked "
        "about instead. Fainting does raise one. If you feel worse, say so or contact a "
        "clinician rather than waiting to be asked: this system is not watching you between "
        "nights."
    ),
    "level.not_a_diagnosis": (
        "Whatever the colour, it describes one measurement of your heart rate against your "
        "own usual range. It is not a diagnosis and not a judgement about your health. If "
        "you feel unwell, contact a clinician, whatever this screen says."
    ),
    # ---------------------------------------------------------- how mature the baseline is
    "rung.COLD": (
        "The system does not yet know your normal. Nothing can be flagged, and no night "
        "can be called unusual, because there is nothing to compare against."
    ),
    "rung.PRIOR_DOMINATED": (
        "Your normal is still mostly a general estimate rather than yours. Treat anything "
        "it says about an unusual night with caution."
    ),
    "rung.SHRINKING": (
        "Your normal is part yours and part a general estimate, and moves toward yours "
        "with every night measured."
    ),
    "rung.PERSONAL": "Your normal is now built from your own nights.",
    "rung.MATURE": ("Your normal is built from a long enough run of your own nights to be stable."),
    # --------------------------------------------------------------- what a number means
    "metric.rhr": (
        "The middle heart rate across the stretch you slept. The middle value is used "
        "rather than the average so a few odd readings cannot drag it."
    ),
    "metric.baseline": (
        "Your own normal, worked out from the middle of your recent nights. Not an average "
        "of other people."
    ),
    "metric.band": (
        "How much you vary from night to night. A night inside this band is an ordinary "
        "night for you."
    ),
    "metric.gap": (
        "How far this night sat above or below your own normal. This is the number the "
        "system actually judges."
    ),
    "metric.sleep_hours": (
        "How long your watch says you slept. This is the stretch the reading was taken "
        "over, before the waking spells inside it were left out."
    ),
    "metric.coverage": (
        "How many minutes of the night your watch actually measured. Too few and the night "
        "is set aside rather than guessed at."
    ),
    "metric.window_source.sleep": (
        "This reading was taken over the sleep your watch recorded, with the waking spells "
        "inside it left out."
    ),
    "metric.window_source.clock": (
        "Your watch recorded no sleep for this night, so the reading was taken over "
        "midnight to seven in the morning instead."
    ),
    # --------------------------------------------------------------------- the chart
    "chart.how_to_read": (
        "The solid dark line is your sleeping heart rate, one point per night. The two "
        "dashed lines above and below it are the top and bottom of your own usual range, "
        "which narrows as the system learns you. Dots are coloured by what the system "
        "concluded. Gaps are nights your watch recorded too little to measure, and are left "
        "empty rather than joined up."
    ),
    # ----------------------------------------------------------------- citations
    "citation.what_this_means": (
        "This sentence quotes a passage held in this system. The check behind it proves "
        "the quoted words really appear in that passage. It does not prove the sentence "
        "built around them describes the passage fairly, so the whole passage is here to "
        "read."
    ),
    "citation.quote_missing": (
        "The quoted words could not be found in this passage. The sentence above should be "
        "treated as unsupported."
    ),
    # ------------------------------------------------------------------- the pipeline
    "pipeline.how_to_read": (
        "Every night runs through these steps in order. Green steps are arithmetic and "
        "give the same answer every time. Blue steps are the AI working inside a fenced "
        "loop. Purple is you. Red is the safety floor, which runs on anything you type and "
        "can only ever raise urgency. Click any step to see what it did."
    ),
    "pipeline.unrecorded": (
        "The system did not write down what this step did. That is a gap in the record, "
        "not a claim that the step was skipped."
    ),
    "step.collect.what": "Your phone was asked for what your watch had recorded.",
    "step.collect.why": (
        "Nothing else can happen until the readings leave the watch. This runs every half "
        "hour, and a pull that finds nothing new is not written down."
    ),
    "step.store.what": "The readings were saved exactly as they arrived.",
    "step.store.why": (
        "Keeping the raw readings means any later result can be checked back against what "
        "the watch actually said."
    ),
    "step.sleep_window.what": "The stretch you actually slept was found.",
    "step.sleep_window.why": (
        "Measuring across time you were awake mixes waking heart rate into the number, "
        "which both raises it and makes it jump about. Using the sleep your watch recorded "
        "avoids that where it can."
    ),
    "step.features.what": "The whole night was reduced to one number.",
    "step.features.why": (
        "One comparable number per night is what makes it possible to say a night was "
        "unusual for you."
    ),
    "step.baseline.what": "Your own normal, and how much you vary, were worked out.",
    "step.baseline.why": (
        "Resting heart rate differs enormously between people, so a general threshold is "
        "meaningless. Everything here is judged against you."
    ),
    "step.subtract_explained.what": "Anything already explained was taken off first.",
    "step.subtract_explained.why": (
        "A recorded evening workout raises resting heart rate for hours afterwards. "
        "Subtracting that keeps exercise from being mistaken for illness."
    ),
    "step.detect.what": "The night was compared against your own range.",
    "step.detect.why": (
        "This is the only step that decides whether anything else happens. It is "
        "arithmetic, and no AI takes part in it."
    ),
    "step.safety_floor.what": (
        "Anything you said about how you feel was checked against a fixed list of "
        "symptoms, over time rather than one message at a time."
    ),
    "step.safety_floor.why": (
        "This is the layer that can overrule every other layer, and it is plain rules "
        "rather than AI, so it cannot be talked round. Some symptoms send you straight to "
        "urgent care on their own. Others matter when two of them turn up together, or "
        "when one keeps going for several nights, and both of those need a memory of what "
        "you have said before, not just tonight's message. Until this was fixed the system "
        "only ever read one message at a time, so a symptom that went on for a week, or a "
        "second symptom that appeared the next day, counted for nothing. Symptoms with no "
        "good evidence behind a rule are still written down here, so they can be asked "
        "about, without pretending to route your care."
    ),
    "step.episode_open.what": (
        "Whether this night started an investigation. It takes two clearly raised nights "
        "in a row, so a single raised night, however high, opens nothing."
    ),
    "step.episode_open.why": (
        "Single raised nights are common and mostly harmless: a late drink, a short night, "
        "a warm room. Acting on every one of them would mean interrupting you constantly "
        "for nothing, so the system waits for a second one before it looks into anything. "
        "Both nights have to be clearly raised. A mildly raised night beside a clearly "
        "raised one does not count, in either order, and mildly raised nights never open "
        "anything however many there are. Nothing opens at all until the system has enough "
        "of your own nights "
        "to know your normal. Only one investigation runs at a time, so a run of raised "
        "nights is looked at as one thing rather than as several alarms."
    ),
    "step.preload.what": "A fixed set of readings was fetched before the AI ran.",
    "step.preload.why": (
        "The AI starts from the same facts every time rather than choosing what to look at "
        "first, which makes what it did afterwards comparable between nights."
    ),
    "step.investigate.what": "The AI chose which tools to call, and called them.",
    "step.investigate.why": (
        "It can only call tools on a fixed list, and every call is recorded. It has no way "
        "to reach anything not on that list."
    ),
    "step.believe.what": "Twelve possible causes were weighed against each other.",
    "step.believe.why": (
        "This is exact arithmetic over every combination of those causes, not the AI "
        "guessing. The same evidence gives the same answer every time."
    ),
    "step.decide.what": "Whether to interrupt you was decided.",
    "step.decide.why": (
        "A question is only worth asking if your answer would change what happens next by "
        "more than the cost of interrupting you. Most nights it is not."
    ),
    "step.ask.what": "The question was put into words and sent to you.",
    "step.ask.why": (
        "The investigation then stops and waits. Nothing about your symptoms is assumed "
        "while it waits."
    ),
    "step.answer.what": "You replied.",
    "step.answer.why": (
        "Your answer is the only source of anything about how you feel. Where you have not "
        "answered, that stays unknown rather than being filled in."
    ),
    "step.conclude.what": "A conclusion was drafted, with its sources attached.",
    "step.conclude.why": (
        "Any sentence that did not quote a real passage was removed before you could see it."
    ),
    "step.critique.what": "The AI read its own draft back.",
    "step.critique.why": (
        "At this point it can only remove claims, never add them, so this step can make "
        "the conclusion smaller and never larger."
    ),
    "step.review.what": "The draft waited for a person.",
    "step.review.why": (
        "A person can approve, edit, reject or escalate it. Nothing reaches you as a "
        "settled conclusion without passing this point."
    ),
    "step.deliver.what": "The conclusion was saved and sent.",
    "step.deliver.why": (
        "It goes to your record, this dashboard and the tamper-evident log at the same "
        "time, so the copy you read is the copy that was kept."
    ),
    "step.safety_phrase_rules.what": "What you wrote was checked against fixed phrase rules.",
    "step.safety_phrase_rules.why": (
        "These are a plain list of phrases, not a model. They run before the AI, and "
        "nothing the AI says can lower what they set. They can only raise urgency."
    ),
    "step.safety_triage.what": "A short published checklist was worked through.",
    "step.safety_triage.why": (
        "The cut-off comes from the study that published the checklist rather than from a "
        "threshold chosen here, and it is only applied to the people that study covered."
    ),
    # ---------------------------------------------------------------------- the record
    "record.what_it_is": (
        "Every action the system took, in order, each one locked to the one before it. If "
        "any entry were altered afterwards, the chain would no longer add up and this page "
        "would say so."
    ),
    "record.empty": (
        "Nothing has been recorded for this person yet. This is an empty record, not a "
        "failed check."
    ),
    # -------------------------------------------------------------------- doctor summary
    "handover.what_it_is": (
        "A short written summary of what this system observed, in the order a clinician "
        "expects to read it. It states what it is not, so nobody mistakes it for a "
        "diagnosis. Read it before you send it: it is your health information and where it "
        "goes is your decision."
    ),
    # --------------------------------------------------------------------- system status
    "status.what_it_is": (
        "Whether each part of the system is working right now. When something here is "
        "amber or red, the line says what stops working as a result."
    ),
}

KEYS: tuple[str, ...] = tuple(TEXT)


def text(key: str) -> str:
    """The sentence for a key.

    A missing key raises rather than returning an empty string. A screen that silently
    renders nothing where an explanation should be is the failure this module exists to
    prevent, and it is exactly what a `.get(key, "")` would produce.
    """
    try:
        return TEXT[key]
    except KeyError as exc:
        raise KeyError(
            f"No explanation is written for {key!r}. Add it to wha/ui/explain.py"
        ) from exc


# Rungs at which the band has shrunk toward this person enough for "your usual range" to
# be a statement about them.
_PERSONAL_RUNGS = {"SHRINKING", "PERSONAL", "MATURE"}


def level(value: str, rung: str | None = None) -> str:
    """What a detection level means, qualified by how well the system knows the person.

    Passing the rung is not optional politeness. Without it a screen tells somebody on a
    three-night baseline that their night was inside "your usual range", when that range
    is the population estimate and nothing about it is theirs yet.
    """
    sentence = text(f"level.{value}")
    if rung is None or rung in _PERSONAL_RUNGS or value == "NA":
        return sentence

    return (
        sentence.replace("your usual range", "the usual range for an adult")
        + " "
        + text("level.immature_note")
    )


def rung(value: str) -> str:
    """What the maturity of the baseline means for what the system can claim."""
    return text(f"rung.{value}")


def step(step_id: str, part: str = "what") -> str:
    """What a pipeline step did, or why it exists."""
    return text(f"step.{step_id}.{part}")
