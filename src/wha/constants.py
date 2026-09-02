"""Constants for Wearable Health Early Warning Agent (WHA).

All constants are single-sourced here as specified in plan/02-contracts.md section 4.
"""

# --- coverage and quality -------------------------------------------------
MIN_NOCTURNAL_MINUTES = 180  # 3h of the 7h window
HR_PLAUSIBLE_MIN_BPM = 25
HR_PLAUSIBLE_MAX_BPM = 220
INGEST_STALE_WARN_HOURS = 36  # status strip turns amber
INGEST_STALE_REFUSE_HOURS = 72  # nightly batch refuses rather than guessing
# How far back the first-run catch up scores nights. The watch holds roughly a month, and
# scoring what it hands over is what builds the baseline; without this a new install shows
# an empty dashboard until the 09:00 cron.
STARTUP_CATCHUP_DAYS = 30

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
# Leota et al. 2025, Nat Commun 16:3297, "high strain" column.
EXERCISE_EFFECT_BPM = {"0-2h": 4.14, "2-4h": 2.91, "4-6h": 1.58}
EXERCISE_LOOKBACK_HOURS = 6
SHORT_SLEEP_HOURS = 5.5  # covariate only, never subtracted

# --- forecast (advisory, never sets level or flagged) ----------------------
FORECAST_MODEL = "amazon/chronos-bolt-small"  # swept in the ablation
FORECAST_MIN_NIGHTS = 5  # below this: status TOO_FEW_NIGHTS
FORECAST_Q_LO = 0.10
FORECAST_Q_HI = 0.90
FORECAST_HALF_WIDTH_FLOOR_BPM = 1.0  # a confident model can return a zero-width band
FORECAST_AS_EVIDENCE = True  # ablation toggle for the belief contribution
FORECAST_EVIDENCE_SD_BPM = 2.5  # deliberately wide: it observes the same night

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
# Same utility units. Annotated "Swept" here and in plan/02-contracts.md, and exposed to
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
INTERRUPTION_BUDGET_PER_WEEK = 2
DEPTH_BUDGET_PER_EPISODE = 5

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
