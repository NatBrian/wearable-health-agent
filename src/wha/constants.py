"""Constants for Wearable Health Early Warning Agent (WHA).

All constants are single-sourced here as specified in docs/CONTRACTS.md section 4.
"""

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
POP_PRIOR_CITATION_PLAIN = "a 2024 study of 525 adults, published in PLOS Digital Health"
POP_PRIOR_CITATION = "Bloomfield et al. 2024, PLOS Digital Health 3(4):e0000473, n=525"

# --- detection ------------------------------------------------------------
# Alavi et al. 2022, Nat Med 28:175-184. NightSignal transitions at 3, red at 4.
DETECT_YELLOW_BPM = 3.0
DETECT_RED_BPM = 4.0
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

# --- forecast (advisory, never sets level or flagged) ----------------------
FORECAST_MODEL = "amazon/chronos-bolt-small"  # swept in the ablation
FORECAST_MIN_NIGHTS = 5  # below this: status TOO_FEW_NIGHTS
FORECAST_Q_LO = 0.10
FORECAST_Q_HI = 0.90
FORECAST_HALF_WIDTH_FLOOR_BPM = 1.0  # a confident model can return a zero-width band
# FORECAST_AS_EVIDENCE and FORECAST_EVIDENCE_SD_BPM were removed on 4 September 2026.
# They asserted that the forecast contributed to the belief model and named an ablation
# toggle for it. No such contribution ever existed: there is no forecast log-factor in
# wha.belief, and both constants were read by nothing anywhere in the codebase.
#
# They were not reinstated, because the evidence does not support the path they described.
# No study was found showing that a forecast residual carries information about WHICH
# cause is present, which is what the belief model needs. Alavi et al. 2022, the source of
# this system's detection thresholds, compared three detectors on this exact problem and
# measured plain baseline deviation (NightSignal) at 78 percent sensitivity against 54
# percent for CuSum and 44 percent for RHRAD at the same false-signal rate: the simplest
# method beat both forecast-style ones.
#
# The forecast now actually runs and is shown as advisory context, which is what the
# heading above this block has always said it is. See docs/RESEARCH-AGENTIC-TRIAGE.md.

# --- belief model ---------------------------------------------------------
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
#     0.05     0.825          0.80
#     0.10     0.725          0.55
#     0.15     0.675          0.40
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
    "5-13 percent actionable. Systematic review, Front Digit Health 2022;4:843747"
)

# How many turns a conversation the person is already in may run to.
#
# Tu et al., Towards conversational diagnostic artificial intelligence, Nature
# 2025;642:442-450, report that "both AMIE and the PCPs were able to acquire the
# information necessary for formulating an accurate differential in the early stages
# (first ten turns)", with comparable performance at all conversation lengths. Ten is
# where the information was in hand; beyond it that study measured no gain.
CONVERSATION_MAX_TURNS = 10

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

# How strongly sensor artifact must lead the differential before the system asks for a
# hand-taken reading instead of a question.
#
# UNEVIDENCED. No study says where this belongs. It exists because the alternative was a
# limb that never ran at all: ActionKind.MEASURE appeared only in the graph's router, the
# policy never selected it, and the measurements table had never held a row. Set at the
# level where sensor artifact is clearly the leading explanation rather than merely
# present, so a spot check is asked for rarely. Disclosed in docs/DISCLOSURES.md.
MEASURE_MIN_LEADING_PROBABILITY = 0.5

# --- episode lifecycle ----------------------------------------------------
ANSWER_TIMEOUT_HOURS = 36
MEASUREMENT_TIMEOUT_HOURS = 24
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
