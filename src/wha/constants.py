"""Constants for Wearable Health Early Warning Agent (WHA).

All constants are single-sourced here as specified in docs/CONTRACTS.md section 4.
"""

# Dashboard display intervals and control bounds. These are operating parameters, not
# clinical thresholds. The API publishes them so browser copy and inputs stay aligned.
DASHBOARD_STEPS_AVERAGE_DAYS = 7
HISTORY_WINDOW_DAYS = [30, 60, 90, 365]
POLICY_COST_WEIGHT_UI_STEP = 0.01
# Display-only deadband retained from the original Vite dashboard. It describes residual
# movement and does not alter a detection level, urgency, or clinical action.
DASHBOARD_RESIDUAL_DIRECTION_FLOOR_BPM = 0.5

# --- coverage and quality -------------------------------------------------
MIN_NOCTURNAL_MINUTES = 180  # 3h of measured sleep

# --- the window a night is measured over ----------------------------------
# Health Connect reports sleep as sessions of contiguous stages. Stages inside a session
# abut one another; separate sessions are hours apart. Sixty minutes cleanly separates the
# two and needs no session identifier, which the stored rows do not carry.
SLEEP_SESSION_GAP_MINUTES = 60

# Naps are excluded from the reading rather than pooled with overnight sleep.
# Whitehurst, Naji and Mednick 2018: 32 adults, within-subjects, polysomnography and ECG,
# a daytime nap and a night of sleep at least a week apart. RR intervals were longer, so
# heart rate was lower, during nighttime sleep than during daytime naps in both stage 2
# and slow wave sleep. Pooling the two would mix distributions with different means and
# bias the night's reading by however much the person happened to nap, which is precisely
# the night-to-night noise this window exists to remove.
NAP_EXCLUSION_CITATION = (
    "Whitehurst, Naji and Mednick 2018, Neurobiology of Sleep and Circadian Rhythms 5:52-57"
)
NAP_EXCLUSION_CITATION_PLAIN = (
    "a 2018 laboratory study of 32 adults comparing naps with overnight sleep"
)
# Measuring over the period the device reports as sleep, rather than a fixed clock window.
SLEEP_WINDOW_CITATION = "Dial et al. 2025, Physiological Reports 13:e70527"
SLEEP_WINDOW_CITATION_PLAIN = "a 2025 validation study of consumer wearables"

# Why the reading comes from sleep rather than from the whole day.
#
# Daytime heart rate measures what a person was doing. Standing up, coffee, a flight of
# stairs move it by tens of bpm; an infection moves it by 1.6 to 5. The signal is real and
# buried. Sleep is the closest a wrist device gets to a controlled measurement: one
# posture, no motion artefact, no volitional input, at roughly the same time each night.
#
# Mishica et al. compared nocturnal against morning heart rate measures and found morning
# values significantly more variable, concluding that during sleep "individuals are no
# longer affected by external stimuli and therefore, enhanced reliability may exist".
DAYTIME_EXCLUSION_CITATION = (
    "Mishica et al. 2022, PLoS One 17(1):e0262333, nocturnal versus morning heart rate measures"
)
DAYTIME_EXCLUSION_CITATION_PLAIN = (
    "a 2022 study comparing overnight with morning heart rate measurements"
)
HR_PLAUSIBLE_MIN_BPM = 25
HR_PLAUSIBLE_MAX_BPM = 220
INGEST_STALE_WARN_HOURS = 36  # status strip turns amber
INGEST_STALE_REFUSE_HOURS = 72  # nightly batch refuses rather than guessing
# How far back the first-run catch up scores nights. The watch holds roughly a month, and
# scoring what it hands over is what builds the baseline; without this a new install shows
# an empty dashboard until the 09:00 cron.
STARTUP_CATCHUP_DAYS = 30

# A night is scored when its sleep has been recorded, not at a fixed hour. Re-scoring a
# trailing window every few hours means someone who wakes at 11:00, or works nights, gets
# the same treatment as someone who wakes at 07:00.
NIGHTLY_RESCORE_INTERVAL_HOURS = 3
NIGHTLY_RESCORE_DAYS = 3

# How far back the dashboard looks when reporting nights with no reading. This is a
# reporting window, NOT a threshold: the pipeline behaves identically at three nights or
# thirty. It is named here because the system also has real night-count thresholds
# (FORECAST_MIN_NIGHTS and the rung ladder, one of whose boundaries is also 7), and a bare
# 7 in the interface is indistinguishable from those.
RECENT_NIGHTS_WINDOW = 7

# Defaults for the synthetic fallback source used when no live bridge is configured.
# Not clinical figures: base_bpm is a plausible adult nocturnal resting heart rate, and the
# seed exists only so the fallback is reproducible.
DEFAULT_SYNTHETIC_BASE_BPM = 60.0
DEFAULT_SYNTHETIC_SEED = 1

# --- baseline ladder ------------------------------------------------------
RUNG_COLD_MAX_NIGHTS = 2  # 0-2   -> COLD
RUNG_PRIOR_MAX_NIGHTS = 6  # 3-6   -> PRIOR_DOMINATED
RUNG_SHRINKING_MAX_NIGHTS = 13  # 7-13  -> SHRINKING
RUNG_PERSONAL_MAX_NIGHTS = 27  # 14-27 -> PERSONAL, 28+ -> MATURE

BASELINE_WINDOW_NIGHTS = 28  # trailing window for the personal estimate
SHRINKAGE_PSEUDO_NIGHTS = 7.0  # k in w = n / (n + k)

# Nights of the person's own data before the baseline is theirs rather than borrowed.
#
# NightSignal, the source of DETECT_YELLOW_BPM and DETECT_RED_BPM below, uses "the
# streaming median of average overnight RHR" per individual, with no population blending
# at all, and reports that "for over 80% of the participants, the proper baseline was
# observed after only seven nights" to within two bpm. Its thresholds are therefore
# deviations above a person's OWN median.
#
# Shrinking the centre toward the population mean and then applying those thresholds to it
# is a category error. Because the trailing window caps n at BASELINE_WINDOW_NIGHTS, the
# shrink weight caps at 28/35 = 0.8, so a fifth of the population prior never washes out.
# Measured on a steady subject after 200 nights of their own data: someone whose true
# sleeping RHR is 45 carries a permanent -3.5 bpm residual and would need a 6.5 bpm rise to
# reach YELLOW, when infection raises nocturnal RHR by roughly 1.6 to 5; someone at 80
# carries +3.5 and sits at YELLOW every night while perfectly healthy. The detector is
# tuned to a 3 to 4 bpm change while carrying up to a 4 bpm bias from the prior alone.
#
# Above this count the centre is the person's own median, matching the cited method. Below
# it the shrinkage estimate is kept, because a median over one or two nights is noise, and
# nothing is flagged at all.
BASELINE_MIN_NIGHTS_PERSONAL = 7
BASELINE_PERSONAL_CITATION = (
    "Alavi et al. 2022, Nature Medicine 28:175-184 (NightSignal): per-individual streaming "
    "median, baseline established for over 80 percent of participants within seven nights"
)
BASELINE_SCALE_FLOOR_BPM = 1.5  # MAD collapses to 0 on quantised data
MAD_TO_SD_FACTOR = 1.4826  # scaled MAD -> sd-equivalent

# What the band's WIDTH shrinks toward before enough of a person's own nights exist.
#
# This used to be POP_PRIOR_RHR_SD_BPM, 8.64, and that was a category error of the same
# shape as the one already corrected on the centre, in the other direction. 8.64 is
# Bloomfield's BETWEEN-PERSON spread: how much 525 different adults differ from each
# other. The band's width is a WITHIN-PERSON quantity: how much one person differs from
# themselves from night to night. Borrowing one for the other inflated every band, and
# because the trailing window caps n at 28 the shrink weight caps at 0.8, so a fifth of a
# between-person spread never washed out however long the watch was worn.
#
# That matters because robust_z is the residual divided by this width, and robust_z is the
# unit the two extreme heart rate rules in red_flags.yaml are written in. Their rationale,
# "six robust standard deviations is well beyond any confounder in the table", is only
# true if the standard deviation is the person's own.
#
# MEASURED, not assumed: 3.71 bpm is the median scaled MAD of 107 people's own overnight
# readings in an archive of past wearable data. Reproduce with
# `uv run python experiments/detection/cohort/band_width.py`, which also reports what this changes:
# the mature band narrows from 4.10 to 3.11 bpm, and the extreme heart rate rules would
# fire on 32 of 7,079 nights rather than 9, one per 31 person-weeks rather than one per
# 112. Recorded in docs/KNOWLEDGE-CHANGELOG.md.
#
# Limitations, stated rather than buried: those are Fitbit users measured over the
# midnight-to-07:00 clock window, not this build's recorded-sleep window, and a
# healthier-than-average research cohort. It is a starting guess that stops mattering once
# the person's own nights arrive, which is exactly what a prior is for.
WITHIN_PERSON_SCALE_PRIOR_BPM = 3.71
WITHIN_PERSON_SCALE_CITATION = (
    "derived by this project from an archive of past wearable readings, not from a "
    "clinical study, and reproducible with experiments/detection/cohort/band_width.py. "
    "See experiments/README.md for what that is and is not worth."
)

# Population prior for nocturnal RHR.
# Bloomfield et al. 2024, PLOS Digital Health 3(4):e0000473, n=525, Oura.
POP_PRIOR_RHR_MEAN_BPM = 62.75
POP_PRIOR_RHR_SD_BPM = 8.64
# Rendered to the person alongside the figure it justifies. Held as strings rather than
# retyped in the interface so the citation cannot drift away from the number.
#
# Two forms on purpose. Journal notation like "3(4):e0000473" is volume, issue and article
# number, which a reader who is not an academic reads as a corrupted string on a dashboard
# otherwise written in plain English. The plain form is what gets shown; the full form
# stays one click away so the claim is still checkable.
POP_PRIOR_CITATION_PLAIN = "a 2024 study of 525 first-year university students, published in PLOS Digital Health"  # Not "525 adults". They were first-year students aged roughly 18 to 24, which is a
# narrower and younger group than that phrasing implies, and resting heart rate
# varies with age and fitness. Corrected 5 September 2026.
POP_PRIOR_CITATION = "Bloomfield et al. 2024, PLOS Digital Health 3(4):e0000473, n=525"

# --- detection ------------------------------------------------------------
# Alavi et al. 2022, Nat Med 28:175-184. NightSignal transitions at 3, red at 4.
DETECT_YELLOW_BPM = 3.0
DETECT_RED_BPM = 4.0
# Consecutive nights, ALL of them RED, which is the published rule: NightSignal raises a
# red alert when the overnight reading is at or above baseline + 4 on two consecutive
# nights. This build used to flag on two consecutive raised nights with at least ONE red,
# so red followed by yellow fired as well, while still quoting NightSignal's sensitivity
# as support. Measured on the cohort, the looser rule bought 6.7 points of sensitivity for
# considerably more investigations into healthy people. See wha/detect/detector.py and
# experiments/detection/cohort/sweep.py.
DETECT_PERSISTENCE_NIGHTS = 2
DETECT_CITATION_PLAIN = "a 2022 study published in Nature Medicine, known as NightSignal"
DETECT_CITATION = "Alavi et al. 2022, Nature Medicine 28:175-184 (NightSignal)"
# Only elevation is investigated. The thresholds above are cited; this one-sidedness is a
# SCOPE decision rather than a cited finding: infection raises nocturnal heart rate, and a
# low resting heart rate is usually fitness or good rest. Conditions that lower it are out
# of scope and the interface says so rather than leaving the reader to infer it.
DETECT_DIRECTION_NOTE = (
    "Only nights above the range are looked into. Infection raises resting heart rate; "
    "a low one is usually fitness or good rest. This system does not look for conditions "
    "that lower it."
)

# --- explained variance ---------------------------------------------------
# Leota et al. 2025, Nat Commun 16:3297. Table of nocturnal RHR contrasts, read from the
# paper on 4 September 2026. Full working in docs/CORPUS-VERIFICATION.md.
#
# The paper reports INCREMENTAL contrasts between adjacent strain levels at each ending
# time relative to habitual sleep onset, in beats per minute:
#
#   contrast          -10h   -8h   -6h   -4h   -2h     0    +2h
#   Light - None      0.49  0.47  0.40  0.33  0.45  2.02   6.50
#   Mod. - Light      0.37  0.48  0.54  0.74  1.32  2.39   3.69
#   High - Mod.       0.18  0.46  0.64  0.80  1.14  1.18   1.49
#   Maximal - High    0.88  1.09  1.24  1.34  1.43  1.80   4.25
#
# High strain against no exercise is the sum of the first three rows:
#
#   -10h 1.04   -8h 1.41   -6h 1.58   -4h 1.87   -2h 2.91   0h 5.59   +2h 11.68
#
# What was here before: {"0-2h": 4.14, "2-4h": 2.91, "4-6h": 1.58}. Two of those three
# figures are exactly the paper's high-strain values, at -2h and -6h, which is far too
# precise to be coincidence. But they were assigned to bands one step apart from each
# other: 2.91 is the -2h figure and was labelled the 2-4h band, while 1.58 is the -6h
# figure labelled the 4-6h band. And 4.14 appears nowhere in the table; it sits between
# the -2h (2.91) and 0h (5.59) values and was presumably interpolated.
#
# Corrected to one consistent rule: each band takes the paper's value at the edge of that
# band FURTHEST from sleep onset. That is the smallest figure the paper supports for the
# band, and it is deliberately the conservative direction. This quantity is SUBTRACTED
# from the observed elevation, so over-stating it hides real illness, while under-stating
# it only causes another look. The system's own utilities weigh a missed illness nine
# times a false alarm (UTILITY_MISS_ILLNESS against UTILITY_FALSE_ALARM, derived from
# Pauker and Kassirer 1980), so the smaller figure is the one that matches its own stated
# preference.
EXERCISE_EFFECT_BPM = {"0-2h": 2.91, "2-4h": 1.87, "4-6h": 1.58}
EXERCISE_LOOKBACK_HOURS = 6
SHORT_SLEEP_HOURS = 5.5  # covariate only, never subtracted

# --- forecast: REMOVED 5 September 2026 -----------------------------------
#
# FORECAST_MODEL, FORECAST_MIN_NIGHTS, FORECAST_Q_LO, FORECAST_Q_HI and
# FORECAST_HALF_WIDTH_FLOOR_BPM are gone with wha/detect/forecast.py. A Chronos-Bolt
# time-series foundation model, 182 MB of weights and a prediction every night, produced
# one advisory paragraph that changed nothing.
#
# Removed on a comparison, not on taste. Against an archive of past wearable readings
# the forecast residual separated illness LESS well than the plain baseline residual
# the detector already computes. That is an engineering comparison run by this
# project, not clinical evidence; it is recorded in experiments/forecasting/.
#
# An AUC of 0.5 is no separation, so the forecast separates illness WORSE than the number
# already on hand. The two correlate at 0.73, so it is measuring something slightly
# different; that something is just not more useful. Across 30 labelled infections it
# caught ONE the detector missed at the most generous setting and none at tighter ones.
#
# Alavi et al. 2022, the source of this system's thresholds, points the same way: it
# measured plain baseline deviation at 78 percent sensitivity against 54 for CuSum and 44
# for RHRAD, both forecast-style detectors.
#
# `forecast_status` stays in the schema, set to NOT_RUN, so databases written before this
# still open and old rows still read.
#
# The dependency is gone too: chronos-forecasting, accelerate and einops are removed from
# pyproject.toml. TORCH IS NOT, and the refinement plan was wrong to expect it to be:
# sentence-transformers needs it for the bge-small embeddings the hybrid retrieval
# actually uses, so removing it would have broken search.

# --- naming the source of a quoted passage --------------------------------
#
# A citation rendered as "(medlineplus_4744#c0)" is traceable and not readable, and the
# MedlinePlus licence is attribution-only: the National Library of Medicine has to be
# NAMED wherever its text is shown, not implied by an identifier prefix. The same labels
# also tell a person at a glance whether they are reading general background about a
# condition or a rule this system applies to them, which is the distinction that matters
# most when the passage sits underneath a piece of health advice.
#
# Here rather than under ui/, because the phone needs them too. They used to live in
# wha/ui/components/citations.py, and the Telegram path correctly refuses to import
# anything under ui/, so a MedlinePlus passage arrived on a real phone labelled
# `Sources: Fever`, crediting nobody. Constants are served by /config, so a replacement
# front end gets them over HTTP like everything else.
MEDLINEPLUS_LABEL = "MedlinePlus, National Library of Medicine"
SOURCE_LABEL_PREFIXES: dict[str, str] = {
    "medlineplus": MEDLINEPLUS_LABEL,
    "escalation": "this system's safety rules",
    "method": "how this system measures you",
    "evidence": "the evidence behind a question it asks",
    "confounder": "the evidence behind a competing explanation",
    "watch_record": "your wearable record",
}
SOURCE_LABEL_FALLBACK = "this repository's own knowledge"
EXTERNAL_SOURCE_PREFIX = "medlineplus"
ATTRIBUTION_NOTE = (
    "Passages from MedlinePlus come from the National Library of Medicine and are used "
    "with attribution. They are general information about a condition, not about you, "
    "and say nothing about your own readings."
)

# --- belief model ---------------------------------------------------------
# How long after an illness the recovery_tail cause stays raised.
#
# Radin et al., JAMA Netw Open 2021;4(7):e2115959, n=234 COVID-positive against 641
# symptomatic negative: resting heart rate "did not return to baseline until roughly 79
# days after symptom onset". causes.yaml already says the belief model "raises it sharply
# when a closed illness episode exists within the published tail window", and no code
# anywhere looked for one, so the boost had never fired.
RECOVERY_TAIL_DAYS = 79
N_CAUSES = 12
BELIEF_STATE_COUNT = 4096  # 2**12, enumerated exactly. Microseconds
RESIDUAL_OBS_SD_BPM = 1.2  # measurement plus model noise on one night
LEAK_EFFECT_SD_BPM = 3.0  # width of the `unexplained` effect prior

# --- policy: decision utilities, not a hand-set threshold ------------------
# Utility over (decision, truth). Same units throughout.
# The testing threshold is DERIVED, not asserted:
#   P* = |U_FALSE_ALARM| / (|U_FALSE_ALARM| + |U_MISS|) = 1 / (1 + 9) = 0.10
# which coincides with Pauker & Kassirer 1980, NEJM 302(20):1109-17.
UTILITY_MISS_ILLNESS = -9.0  # concluded benign, was illness
UTILITY_FALSE_ALARM = -1.0  # concluded illness, was benign
UTILITY_CORRECT = 0.0
# Same utility units. Annotated "Swept" here and in docs/CONTRACTS.md, and exposed to
# the user as policy_cost_weight, so this is a tuning parameter rather than a clinical
# figure. Set from the sweep in wha.eval.policy_oracle, measured over 40 simulated cases
# split evenly between infections and benign mimics presenting identically:
#
#   weight   accuracy   interruptions per episode
#   Lowering it buys accuracy by asking more often, and raising it buys quiet by
#   asking less. The sweep behind that trade is a self-scored simulation and lives
#   in experiments/policy-simulation/, not here.
#     0.30     0.600          0.25      <- previous value
#     0.50     0.525          0.05
#     1.00     0.500          0.00      (degenerates to never asking)
#
# 0.15 is not the accuracy-maximising point, deliberately. It buys a materially wider
# margin over the threshold-only comparator (0.500) while still spending well under one
# question per episode, so the weekly budget of two remains the binding constraint and
# the quiet band that makes EVSI worth having is preserved. Picking 0.05 would maximise
# the metric by nearly always asking, which is the alarm fatigue this project exists to
# avoid.
POLICY_COST_PER_INTERRUPT = 0.15
# Two different resources, which were previously one counter and should never have been.
#
# The alarm fatigue evidence is about UNSOLICITED alarms: 72 to 99 percent of clinical
# monitor alarms are technically false or non-actionable and only 5 to 13 percent are
# actionable, and the consequence is desensitisation and delayed response (systematic
# review, Front Digit Health 2022;4:843747). That is an argument about how often a system
# may contact a person who is not asking. It is not an argument for cutting off a
# conversation the person is already having.
#
# Counting both against one allowance of two meant a follow-up question inside a live
# conversation cost the same as a push notification on an unrelated day, so the agent could
# never ask more than two questions in a week and in practice asked one per episode. A
# system whose only information beyond a heart rate is what the person tells it, when
# history-taking alone yields the final diagnosis in 76 percent of cases (Peterson et al.,
# West J Med 1992;156(2):163-5), should not be spending its best instrument that way.
INTERRUPTION_BUDGET_PER_WEEK = 2  # unsolicited contacts only
INTERRUPTION_BUDGET_CITATION = (
    "Alarm fatigue: 72-99 percent of clinical monitor alarms are non-actionable, only "
    "5-13 percent actionable. Systematic review, Front Digit Health 2022;4:843747. "
    "NOTE: that review is about INTENSIVE CARE BEDSIDE MONITORS, not consumer "
    "notifications, so it establishes the direction of the argument and not this number."
)
# WHAT ACTUALLY KEEPS THIS SYSTEM QUIET, measured rather than assumed.
#
# It is not this counter. In everything this project has run, the system opens an
# investigation rarely enough that the weekly allowance is never approached.
# question per investigation, so two a week is never approached. In a live run with the
# whole allowance unspent the agent asked one question and stopped, because after the
# answer the EVSI of every remaining probe had fallen below its interruption cost.
#
# The quiet band is the control, and it is the better story: the arithmetic decides an
# interruption is not worth its cost, rather than a counter running out. Reproduce the
# alert rate with `uv run python experiments/detection/cohort/report.py`.
#
# The counter is kept anyway. It costs nothing, it is a genuine backstop, and the alert
# rate moved when the persistence rule was tightened, so removing a safety net to save
# nothing is not a trade worth making.
INTERRUPTION_BUDGET_NOTE = (
    "This counter has never been reached in anything this project has run. What keeps the "
    "system quiet is the arithmetic deciding a question is worth less than the cost of "
    "asking it, not this cap. The cap is a backstop."
)

# How many turns a conversation the person is already in may run to.
#
# Tu et al., Towards conversational diagnostic artificial intelligence, Nature
# 2025;642:442-450, report that "both AMIE and the PCPs were able to acquire the
# information necessary for formulating an accurate differential in the early stages
# (first ten turns)", with comparable performance at all conversation lengths. Ten is
# where the information was in hand; beyond it that study measured no gain.
CONVERSATION_MAX_TURNS = 10

# The gap after which the next message starts a new consultation, and the turn counter
# begins again.
#
# THE LIMIT IS PER CONSULTATION, NOT PER LIFETIME. Tu et al. measured ten turns within one
# consultation with one patient; nothing in that paper says a person gets ten turns and
# then silence. The counter was computed over `load_transcript(limit=1000)`, which selects
# every row this subject has ever produced with no episode, session or date filter, and
# nothing anywhere deletes or resets conversation_turns. So after twenty stored rows the
# agent stopped conversing permanently, for the life of the database, and the only reply
# any future message could get was "we have been going back and forth".
#
# UNEVIDENCED. No study was found stating how long a gap ends a consultation. Six hours is
# chosen so that a morning exchange and an evening one are separate, which is the shortest
# span that clearly separates two occasions of somebody picking up their phone. The
# direction it errs in is more conversation rather than less, and the deterministic safety
# floor runs on every message regardless of which session it belongs to.
CONVERSATION_SESSION_GAP_HOURS = 6

# How many agent turns a validated rule may stay incomplete before the presentation is
# resolved conservatively.
#
# UNEVIDENCED. No study says how long it is acceptable to leave someone describing chest
# pain without an answer. It exists because the alternative measured worse: in a live run
# the agent asked the Marburg questions correctly, failed to record the answers, and left
# a person with chest pain in limbo with no urgency at all, which is worse than the
# over-escalation this design replaced. Three is short enough that limbo cannot persist and
# long enough to gather five items. Disclosed in docs/DISCLOSURES.md and on screen.
TRIAGE_MAX_TURNS_BEFORE_ESCALATE = 3
CONVERSATION_DEPTH_CITATION = (
    "Tu et al. 2025, Nature 642:442-450 (AMIE): an accurate differential was reached "
    "within the first ten turns of consultation"
)

# Questions the EVSI policy may ask across one episode, separate from the conversation.
DEPTH_BUDGET_PER_EPISODE = 5

# MEASURE_MIN_LEADING_PROBABILITY was removed on 5 September 2026, with the spot-reading
# limb it gated.
#
# It was 0.5 with no source, and it decided when to ask somebody to count their own pulse
# for thirty seconds in order to judge whether their watch had misread them. Two more
# invented numbers sat behind it, -1.5 and 0.3, the log-factor that answer contributed,
# hardcoded in wha/belief/likelihood.py rather than in a knowledge table.
#
# The idea is weaker than it looks: asking a hand count to adjudicate a wrist sensor asks
# the noisier instrument to judge the less noisy one. And it could not complete anyway,
# because `_resume_value` in the scheduler answered every measurement interrupt with
# "declined" regardless of what the person did.
#
# The honest behaviour when the sensor is the leading explanation is to say the night
# could not be judged. See wha/policy/select.py.

# How long a "see a doctor today" stays current before the banner says how old it is.
#
# UNEVIDENCED, and it is a presentation rule rather than a clinical one. No study says
# when an urgency should stop being displayed, and this is NOT a judgement that the person
# is now safe.
#
# What it encodes is narrower: an instruction with the word "today" in it stops being
# current after a while, either they went or they did not, and this system has no way to
# know which. A red banner that never goes away is one you learn to ignore, which is the
# alarm fatigue this project cites in its own constants.
#
# The urgency is NEVER dropped silently. After this window the banner still appears, still
# says what was concluded and when, and adds that the system does not know what happened
# since. History keeps it either way. Only a person saying they have seen somebody clears
# it, and that is recorded too.
URGENCY_STALE_DAYS = 7

# How much worse a night has to be before an escalation already sent is sent again.
#
# The guard used to be "once per episode, ever". A first sync backfills weeks of history
# and night scoring re-runs every few hours, so an unguarded send would put the same
# escalation on somebody's phone repeatedly, and that reasoning still holds.
#
# What it missed is deterioration. A person whose reading went from six robust deviations
# above their own normal to nine, having already told the system they felt unwell, was
# told nothing the second time, because something had been sent for that investigation
# once. Silence while a person gets worse is the failure this system exists to prevent.
#
# One full robust deviation, expressed in the person's own units rather than in bpm, so it
# means the same thing for somebody who varies by two bpm a night and somebody who varies
# by six. It is not a clinical threshold and is not claimed as one: it is the smallest
# change this system can call a change at all, since its whole scale is the person's own
# night-to-night variation.
ESCALATION_REPEAT_ROBUST_Z_RISE = 1.0

# How many nights an extreme reading may persist before the person is told again, even
# when it has not got any worse.
#
# The rise rule above catches deterioration and nothing else. A reading that stays at seven
# robust deviations above somebody's own normal, night after night, produced one message
# and then silence, and silence after a warning reads as "nothing new" when what it
# actually means is "still far outside your range". Somebody who did not act on the first
# message hears nothing further while it continues.
#
# Two nights, so it is a reminder rather than a nightly alarm. Alarm fatigue is a real harm
# and repeating the same sentence every night is how a warning stops being read. This is a
# judgement about how often to speak, not a clinical threshold, and it is disclosed as one.
ESCALATION_REPEAT_NIGHTS = 2

# --- symptoms over time ---------------------------------------------------
# How many days of silence end a symptom's run.
#
# CITED, and it is the one number here that a literature actually supplies. Respiratory
# illness surveillance cohorts conventionally treat two illnesses as distinct episodes
# when they are separated by at least SEVEN SYMPTOM-FREE DAYS. Shorter intervals appear
# (48 hours in RSV infant studies) and longer ones (21 and 30 days in some community
# cohorts), but seven is the common convention and the illness class is the one this
# system targets: the NightSignal, DETECT and Mishra cohorts are all respiratory.
#
# It is checked against a second, independent case. Saddleback dengue is defined as
# defervescence of at least one day followed by a second fever peak one to two days later,
# and that second peak is the dangerous one. Seven days contains that gap comfortably, so
# a biphasic fever stays ONE illness rather than being scored as two unrelated events.
#
# WHY DAYS OF SILENCE AND NOT CONSECUTIVE NIGHTS. Requiring an unbroken night-by-night run
# would reset a fever to zero because somebody did not pick up their phone on Tuesday.
# Punishing a person's silence is the exact failure this whole change exists to remove.
#
# WHY NOT GREEN NIGHTS. The source says symptom-free, not reading-normal, and those are
# not interchangeable: dengue's critical phase begins as the fever breaks, relative
# bradycardia (Faget's sign) means typhoid, dengue, Legionella and Q fever can run with an
# ordinary pulse, and Radin et al. measured resting heart rate taking on average 79 days to
# return to baseline after COVID symptom onset. A reading coming back to normal is evidence
# about the reading, not about the person.
SYMPTOM_RUN_GAP_DAYS = 7

# The same number, used for whether a new investigation continues a previous one.
# Held separately from SYMPTOM_RUN_GAP_DAYS because they are two decisions that happen to
# share a source, and a later change to one must not silently move the other.
EPISODE_RECURRENCE_LINK_DAYS = 7

# How many nights apart two Tier B symptoms may be and still count as co-occurring.
#
# DERIVED, from this repository's own reviewed numbers rather than invented. red_flags.yaml
# escalates on "two or more co-occurring" Tier B symptoms, and that was implemented as two
# or more IN THE SAME MESSAGE, which is not what the word means: a fever on Monday and
# vomiting on Tuesday co-occur in any ordinary reading. Two nights is the shortest
# persist_nights in that file (rf_poor_intake and rf_persistent_vomiting, both 2), so the
# window is the tightest one the file's own authors already reviewed.
#
# Conservative direction: a WIDER window escalates more often, so the error this carries is
# an unnecessary same-day appointment rather than a missed deterioration. Disclosed on the
# dashboard as DERIVED, not measured.
SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS = 2

# The probe used to follow up an outstanding symptom, and how often it may be re-asked.
#
# WHY THIS RULE EXISTS AT ALL. EVSI scores a question by how much the answer moves the
# belief across twelve CAUSES. Once a cause is settled, asking again is worth nothing, so
# the more certain the system becomes that somebody is ill, the LESS reason it has to
# speak to them. A person reported dizziness, it got worse over the following nights, and
# the system correctly computed that another answer would not change which cause it
# believed in, and said nothing at all. The arithmetic was right and the behaviour was
# indefensible. This rule sits beside it rather than inside it, because adding severity or
# trajectory to the belief table would mean inventing likelihood rows no literature
# supplies.
SYMPTOM_FOLLOWUP_PROBE_ID = "probe_symptoms"

# At most this many follow-ups per investigation.
#
# ASSUMED. No source measures how often to ask an unwell person how they are, and none is
# claimed. Three is chosen so the rule cannot become a nightly alarm across an episode
# whose hard ceiling is EPISODE_MAX_NIGHTS, while still allowing a symptom to be revisited
# more than once. Conservative direction is genuinely ambiguous here, which is why the
# number is small: too many messages is the alarm fatigue this project exists to reduce,
# and too few is the silence it exists to prevent. Bounded on both sides by things that
# are not this number: it stops the moment the person says the symptom has gone, and the
# run itself expires after SYMPTOM_RUN_GAP_DAYS. Marked unevidenced on the dashboard.
SYMPTOM_FOLLOWUP_MAX_PER_EPISODE = 3

# At most one follow-up per night, whatever else happens.
SYMPTOM_FOLLOWUP_MIN_NIGHTS_APART = 1

# --- episode lifecycle ----------------------------------------------------
ANSWER_TIMEOUT_HOURS = 36
MEASUREMENT_TIMEOUT_HOURS = 24

# How long a drafted conclusion waits for a person to check it before it closes UNREVIEWED.
#
# The review checkpoint was auto-approved by a background job fifteen minutes after the
# draft appeared, and the record then said a human had approved it. Nothing may answer on
# the person's behalf, so the episode has to be able to park indefinitely, and something
# has to release it eventually or it parks forever.
#
# Set to ANSWER_TIMEOUT_HOURS deliberately. There is no evidence on how long a person
# should be given to review a wearable early-warning conclusion, so inventing a separate
# figure would be inventing a number. The same window the system already allows for
# answering a question is the honest choice, and a review is a lighter ask than an answer.
# A release records `closed_unreviewed` and is never recorded as an approval.
REVIEW_TIMEOUT_HOURS = ANSWER_TIMEOUT_HOURS
EPISODE_MAX_NIGHTS = 10
EPISODE_MAX_STEPS = 40  # hard graph recursion cap
MAX_TOOL_CALLS_PER_EPISODE = 25  # bounds the free T1 investigation loop

# --- llm ------------------------------------------------------------------
LLM_MAX_TOKENS_FLOOR = 200
LLM_TIMEOUT_SECONDS = 120
LLM_REPAIR_ATTEMPTS = 1  # exactly one, then raise ValidationFailed
TEMP_DETERMINISTIC = 0.0  # extraction, red-flag, critique
TEMP_NATURAL = 0.3  # question phrasing, outcome prose

# --- retrieval ------------------------------------------------------------
CHUNK_TARGET_TOKENS = 400
RRF_K = 60  # reciprocal rank fusion constant
RETRIEVE_TOP_K = 8

# --- outbound -------------------------------------------------------------
OUTBOUND_MAX_CHARS = 900
TELEGRAM_CALLBACK_MAX_BYTES = 64
