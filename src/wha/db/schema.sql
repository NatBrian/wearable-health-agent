-- WHA SQLite Storage Schema
-- Single source of truth from plan/02-contracts.md section 5

CREATE TABLE IF NOT EXISTS subjects (
  subject_id     TEXT PRIMARY KEY,
  label          TEXT NOT NULL,
  source_kind    TEXT NOT NULL CHECK (source_kind IN ('live','synthetic','cohort')),
  timezone       TEXT NOT NULL DEFAULT 'Asia/Singapore',
  created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_payloads (
  id            INTEGER PRIMARY KEY,
  subject_id    TEXT NOT NULL REFERENCES subjects(subject_id),
  fetched_at_utc TEXT NOT NULL,
  source_kind   TEXT NOT NULL,
  sha256        TEXT NOT NULL,
  payload_json  TEXT NOT NULL,
  UNIQUE (subject_id, sha256)
);

CREATE TABLE IF NOT EXISTS heart_rate_samples (
  subject_id TEXT NOT NULL,
  ts_utc     TEXT NOT NULL,
  avg_bpm    REAL NOT NULL,
  min_bpm    REAL,
  max_bpm    REAL,
  origin     TEXT,
  PRIMARY KEY (subject_id, ts_utc)
);

CREATE TABLE IF NOT EXISTS step_buckets (
  subject_id TEXT NOT NULL,
  start_utc  TEXT NOT NULL,
  end_utc    TEXT NOT NULL,
  count      INTEGER NOT NULL,
  PRIMARY KEY (subject_id, start_utc)
);

CREATE TABLE IF NOT EXISTS sleep_stages (
  subject_id TEXT NOT NULL,
  start_utc  TEXT NOT NULL,
  end_utc    TEXT NOT NULL,
  stage      TEXT NOT NULL,
  PRIMARY KEY (subject_id, start_utc)
);

CREATE TABLE IF NOT EXISTS exercise_sessions (
  subject_id TEXT NOT NULL,
  start_utc  TEXT NOT NULL,
  end_utc    TEXT NOT NULL,
  kind       TEXT,
  PRIMARY KEY (subject_id, start_utc)
);

-- Verified present on the device bridge on 2026-09-02. Sparse: oxygen saturation
-- arrives as a handful of spot readings rather than a continuous stream, so a night
-- frequently has none.
CREATE TABLE IF NOT EXISTS oxygen_saturation_samples (
  subject_id TEXT NOT NULL,
  ts_utc     TEXT NOT NULL,
  percentage REAL NOT NULL,
  origin     TEXT,
  PRIMARY KEY (subject_id, ts_utc)
);

CREATE TABLE IF NOT EXISTS distance_buckets (
  subject_id TEXT NOT NULL,
  start_utc  TEXT NOT NULL,
  end_utc    TEXT NOT NULL,
  meters     REAL NOT NULL,
  PRIMARY KEY (subject_id, start_utc)
);

CREATE TABLE IF NOT EXISTS calorie_buckets (
  subject_id    TEXT NOT NULL,
  start_utc     TEXT NOT NULL,
  end_utc       TEXT NOT NULL,
  calories_kcal REAL NOT NULL,
  PRIMARY KEY (subject_id, start_utc)
);

CREATE TABLE IF NOT EXISTS nightly_features (
  subject_id            TEXT NOT NULL,
  night_date            TEXT NOT NULL,
  rhr_bpm               REAL,
  coverage_minutes      INTEGER NOT NULL,
  implausible_dropped   INTEGER NOT NULL DEFAULT 0,
  usable                INTEGER NOT NULL,
  steps_prev_day        INTEGER,
  sleep_hours           REAL,
  exercise_end_offset_h REAL,
  rhr_window_source     TEXT,
  computed_at_utc       TEXT NOT NULL,
  PRIMARY KEY (subject_id, night_date)
);

CREATE TABLE IF NOT EXISTS baselines (
  subject_id    TEXT NOT NULL,
  night_date    TEXT NOT NULL,
  centre_bpm    REAL NOT NULL,
  scale_bpm     REAL NOT NULL,
  usable_nights INTEGER NOT NULL,
  rung          TEXT NOT NULL,
  shrink_weight REAL NOT NULL,
  PRIMARY KEY (subject_id, night_date)
);

CREATE TABLE IF NOT EXISTS detections (
  subject_id      TEXT NOT NULL,
  night_date      TEXT NOT NULL,
  deviation_bpm   REAL,
  robust_z        REAL,
  explained_bpm   REAL NOT NULL DEFAULT 0,
  residual_bpm    REAL,
  level           TEXT NOT NULL CHECK (level IN ('GREEN','YELLOW','RED','NA')),
  flagged         INTEGER NOT NULL,
  forecast_bpm    REAL,
  forecast_lo_bpm REAL,
  forecast_hi_bpm REAL,
  forecast_z      REAL,
  forecast_status TEXT NOT NULL DEFAULT 'NOT_RUN'
                  CHECK (forecast_status IN ('OK','NOT_RUN','TOO_FEW_NIGHTS','FAILED')),
  reasons_json    TEXT NOT NULL,
  PRIMARY KEY (subject_id, night_date)
);

CREATE TABLE IF NOT EXISTS episodes (
  episode_id       TEXT PRIMARY KEY,
  subject_id       TEXT NOT NULL,
  thread_id        TEXT NOT NULL,
  opened_on        TEXT NOT NULL,
  closed_on        TEXT,
  state            TEXT NOT NULL CHECK (state IN
                     ('OPEN','AWAITING_USER','AWAITING_MEASUREMENT',
                      'AWAITING_HUMAN_REVIEW','CLOSED')),
  disposition      TEXT,
  baseline_nights  INTEGER NOT NULL,
  baseline_rung    TEXT NOT NULL,
  step_count       INTEGER NOT NULL DEFAULT 0,
  tool_call_count  INTEGER NOT NULL DEFAULT 0,
  depth_used       INTEGER NOT NULL DEFAULT 0,
  -- The most recent night the agent has reasoned over, so an episode that decided to
  -- observe can be re-entered when a further night arrives rather than sitting forever.
  last_evidence_night TEXT,
  -- v9. Which investigation this one continues, if any, and the gap in days.
  --
  -- Respiratory illness surveillance conventionally separates two episodes by at least
  -- seven symptom-free days; inside that window this is the same illness recurring, not a
  -- new one. Saddleback dengue makes the case concretely: the second fever peak arrives
  -- one to two days after defervescence and is the dangerous one, so treating it as an
  -- unrelated first-ever investigation throws away the fact that matters most.
  --
  -- A linked episode is still its own row. Merging them would break the one-open-episode
  -- invariant and rewrite a closed episode's disposition, and neither is worth it: what
  -- was missing is the CONTEXT, and a pointer carries that.
  preceded_by_episode_id TEXT,
  days_since_previous INTEGER
);
CREATE INDEX IF NOT EXISTS idx_episodes_subject_state ON episodes(subject_id, state);

CREATE TABLE IF NOT EXISTS beliefs (
  episode_id     TEXT NOT NULL,
  seq            INTEGER NOT NULL,
  ts_utc         TEXT NOT NULL,
  trigger        TEXT NOT NULL,
  marginals_json TEXT NOT NULL,
  p_illness      REAL NOT NULL,
  -- Full 4096-state joint log-posterior. The marginals alone cannot reconstruct it,
  -- and without it EVSI silently degrades: every probe that is not the infection probe
  -- scores exactly zero, so explaining-away stops working and the policy stops asking.
  state_logprob_json TEXT,
  PRIMARY KEY (episode_id, seq)
);

CREATE TABLE IF NOT EXISTS interactions (
  id                TEXT PRIMARY KEY,
  episode_id        TEXT NOT NULL,
  probe_id          TEXT NOT NULL,
  question_text     TEXT NOT NULL,
  text_source       TEXT NOT NULL CHECK (text_source IN ('llm','fallback')),
  options_json      TEXT NOT NULL,
  evsi              REAL NOT NULL,
  interruption_cost REAL NOT NULL,
  rejected_json     TEXT NOT NULL,
  answer_option_id  TEXT,
  free_text         TEXT,
  channel           TEXT NOT NULL,
  asked_at_utc      TEXT NOT NULL,
  answered_at_utc   TEXT,
  status            TEXT NOT NULL CHECK (status IN
                      ('PENDING','ANSWERED','DECLINED','TIMED_OUT'))
);
CREATE INDEX IF NOT EXISTS idx_interactions_pending ON interactions(episode_id, status);

CREATE TABLE IF NOT EXISTS measurements (
  id               TEXT PRIMARY KEY,
  episode_id       TEXT NOT NULL,
  kind             TEXT NOT NULL CHECK (kind IN ('spot_resting_hr','wear_tonight')),
  instruction      TEXT NOT NULL,
  requested_at_utc TEXT NOT NULL,
  expires_at_utc   TEXT NOT NULL,
  satisfied_at_utc TEXT,
  result_json      TEXT,
  status           TEXT NOT NULL CHECK (status IN ('PENDING','SATISFIED','TIMED_OUT'))
);

CREATE TABLE IF NOT EXISTS outcomes (
  episode_id     TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  payload_json   TEXT NOT NULL,
  created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
  event_id                 TEXT PRIMARY KEY,
  subject_id               TEXT NOT NULL,
  episode_id               TEXT,
  step_index               INTEGER,
  checkpoint_id            TEXT,
  timestamp_utc            TEXT NOT NULL,
  actor                    TEXT NOT NULL CHECK (actor IN
                             ('agent','human','system','monitor')),
  operation                TEXT NOT NULL,
  control_tier             TEXT CHECK (control_tier IN ('T0','T1','T2','T3','T4','X')),
  input_json               TEXT,
  tool_name                TEXT,
  tool_args_json           TEXT,
  tool_result_json         TEXT,
  permission_decision      TEXT CHECK (permission_decision IN
                             ('allowed','denied','required_approval')),
  sources_json             TEXT,
  output_json              TEXT,
  output_schema_version    TEXT,
  validation_status        TEXT CHECK (validation_status IN ('pass','repaired','failed')),
  human_decision           TEXT,
  human_decision_rationale TEXT,
  model_id                 TEXT,
  prompt_id                TEXT,
  prompt_version           TEXT,
  latency_ms               INTEGER,
  token_usage_json         TEXT,
  safety_event             TEXT NOT NULL DEFAULT 'none',
  prev_hash                TEXT,
  hash                     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_episode ON audit_events(episode_id, timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_audit_safety  ON audit_events(safety_event);

CREATE TABLE IF NOT EXISTS budgets (
  subject_id TEXT NOT NULL,
  week_start TEXT NOT NULL,
  used       INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (subject_id, week_start)
);

CREATE TABLE IF NOT EXISTS system_status (
  id         INTEGER PRIMARY KEY,
  subject_id TEXT,
  ts_utc     TEXT NOT NULL,
  component  TEXT NOT NULL,
  ok         INTEGER NOT NULL,
  detail     TEXT
);
CREATE INDEX IF NOT EXISTS idx_status_recent ON system_status(component, ts_utc);

CREATE TABLE IF NOT EXISTS notifications (
  id             TEXT PRIMARY KEY,
  subject_id     TEXT NOT NULL,
  episode_id     TEXT,
  interaction_id TEXT,
  measurement_id TEXT,
  channel        TEXT NOT NULL,
  kind           TEXT NOT NULL CHECK (kind IN
                   ('QUESTION','MEASUREMENT','ESCALATION','OUTCOME','SYSTEM')),
  payload_json   TEXT NOT NULL,
  queued_at_utc  TEXT NOT NULL,
  sent_at_utc    TEXT,
  external_id    TEXT,
  status         TEXT NOT NULL CHECK (status IN ('QUEUED','SENT','FAILED'))
);

CREATE TABLE IF NOT EXISTS telegram_offset (
  id         INTEGER PRIMARY KEY CHECK (id = 1),
  update_id  INTEGER NOT NULL
);

-- v6. The conversation, and the triage items gathered inside it.
--
-- Talking to the system used to be a text box over a word-overlap lookup that made no
-- model call at all. A real conversation needs a transcript that outlives the process, so
-- the agent can be resumed, the person can scroll back, and the audit can show what was
-- actually said rather than what was last rendered.
CREATE TABLE IF NOT EXISTS conversation_turns (
  id                TEXT PRIMARY KEY,
  episode_id        TEXT,
  subject_id        TEXT NOT NULL,
  seq               INTEGER NOT NULL,
  role              TEXT NOT NULL CHECK (role IN ('user','agent')),
  text              TEXT NOT NULL,
  -- Grounded claims and the passages behind them, and separately the sentences the model
  -- produced from its own knowledge with no citation. Kept apart on purpose: a reader is
  -- entitled to know which is which, and Draelos et al. 2025 measured 5 to 13 percent of
  -- unguarded model answers to patient questions as outright unsafe.
  citations_json    TEXT NOT NULL DEFAULT '[]',
  uncited_json      TEXT NOT NULL DEFAULT '[]',
  -- What the deterministic floor made of this turn, never what the model thought.
  urgency           TEXT,
  triggered_flags_json TEXT NOT NULL DEFAULT '[]',
  asked_item_id     TEXT,
  -- Which discriminator conversation is open. Held here rather than inferred from the
  -- answers gathered so far, because the answers can legitimately be empty for several
  -- turns and the presentation must not be forgotten in between.
  presentation      TEXT,
  created_at_utc    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversation_seq ON conversation_turns(subject_id, seq);

-- Answers to the items of a validated decision rule, gathered in conversation.
-- The model elicits these; wha.safety.triage scores them. Stored separately from
-- interactions because they are rule inputs, not policy questions, and because a score
-- must be reconstructible from what the person actually said.
CREATE TABLE IF NOT EXISTS triage_answers (
  subject_id     TEXT NOT NULL,
  episode_id     TEXT,
  presentation   TEXT NOT NULL,
  item_id        TEXT NOT NULL,
  answer         INTEGER,
  source_text    TEXT,
  recorded_at_utc TEXT NOT NULL,
  PRIMARY KEY (subject_id, presentation, item_id)
);

CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY
);

-- The five standing facts about a person that something in this system actually reads.
--
-- Added 5 September 2026, schema v7. The Marburg Heart Score was tested only on people
-- aged 35 and over, `triage()` takes an `age_years` to enforce that, and nothing ever
-- filled it in, so the rule ran on everybody. In a real run somebody typed "I am 24 and
-- male", the system stored that, then applied a rule never tested on 24 year olds, scored
-- 3 of 5 on three things common in a young adult with a pulled muscle, said urgent, and
-- cited a study of 1,199 people aged 35 and over.
--
-- The test for including a field is whether something CONSUMES it. Weight, height and BMI
-- are deliberately absent: nothing here reads them, and a field nobody reads tells a
-- person their data is being used when it is not. Free-text health history is deliberately
-- absent from this table too, because it would enter the conversation prompt, where the
-- model would reason from it with no grounding and no citation.
CREATE TABLE IF NOT EXISTS subject_profile (
  subject_id       TEXT PRIMARY KEY REFERENCES subjects(subject_id),
  -- Marburg age gate (minimum_age_years) and Marburg item 1.
  age_years        INTEGER,
  -- 'female', 'male' or NULL. Marburg item 1 is "woman 65 or over, or man 55 or over".
  sex              TEXT CHECK (sex IN ('female','male') OR sex IS NULL),
  -- Marburg item 2, pre-filled so the conversation asks the three that genuinely vary.
  -- The item most likely to be misremembered under stress, and the one that never changes.
  known_vascular_disease INTEGER,
  -- The luteal cause in causes.yaml. A standing fact, not worth an interruption.
  menstruates      INTEGER,
  -- Read by nothing, deliberately. It becomes a DISCLOSURE: beta blockers blunt the heart
  -- rate response to infection, so the system says "I am less able to see an infection in
  -- you" rather than silently being worse at its job.
  rate_lowering_medicine INTEGER,
  -- For the doctor, never for the model. Rendered into the SBAR handover and excluded from
  -- every prompt. This is the one place free text is allowed, precisely because it does
  -- not enter the reasoning path.
  notes_for_doctor TEXT,
  updated_at_utc   TEXT NOT NULL
);

-- What the agent actually did in an episode, recorded by the graph rather than inferred.
--
-- Added 5 September 2026, schema v8. The Trace tab listed nine stages and marked EVERY ONE
-- as skipped, on every episode, with an invented reason: "Ask probe not selected by EVSI
-- optimizer" appeared on episodes whose own summary said a question had been asked. The
-- cause was that `get_episode` matched stage names against the `operation` column of the
-- audit log, which holds ten fixed values and none of them is a stage name, so no row
-- could ever match and the fallback branch ran every time.
--
-- The audit log was rejected as the fix. Writing a row per node roughly triples it and
-- buries the tool calls, which are the entries that matter. The graph already knows which
-- nodes ran, so it records that here.
--
-- Also holds the claims the grounding check removed. `stripped_claims` on the episode view
-- was assigned an empty list and never filled, so the panel that exists to show what was
-- taken out of the prose showed a green tick on every episode, including ones where a
-- claim had genuinely been stripped.
CREATE TABLE IF NOT EXISTS episode_traces (
  episode_id     TEXT PRIMARY KEY REFERENCES episodes(episode_id),
  payload_json   TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

-- Symptoms as things that PERSIST, rather than keywords in one message.
--
-- Added 7 September 2026, schema v9. red_flags.yaml has always documented Tier B as
-- "two or more co-occurring, OR one persisting beyond a stated duration", and the
-- persistence half had never once fired: `check_red_flags_deterministic` takes a
-- `symptom_history` argument that no production caller passed, so `history.get(id, 1)`
-- was always 1 and `1 > persist_nights` was never true. Six symptoms carry a
-- persist_nights value and not one of them could escalate on its own.
--
-- It was not merely unwired, it was uncomputable: nothing anywhere recorded that a
-- symptom had been present on a given night. triage_answers upserts and keeps only the
-- latest state. This table is that missing record.
--
-- One row per symptom per night, so "fever on 3 of the last 5 nights" is a query rather
-- than an inference. Rebuilt from conversation_turns text, which was already stored, so
-- no new data is collected from anybody to make this work.
--
-- `present` distinguishes the two silences that look identical without it: 0 means the
-- person SAID it had settled (a negated mention), and no row at all means they did not
-- mention it. Treating those the same is how a resolved symptom and a forgotten one end
-- up with the same consequence.
CREATE TABLE IF NOT EXISTS symptom_observations (
  subject_id      TEXT NOT NULL,
  -- The local date the person was talking about their state on. Symptoms are reported
  -- during the day about how they feel; the night is the unit everything else here is
  -- keyed on, so they are recorded against the local date of the turn.
  night_date      TEXT NOT NULL,
  -- A red_flags.yaml rule id where one matched. Symptoms with no rule are still recorded,
  -- under their own id, because tracking a symptom is a far weaker claim than escalating
  -- on it and is the right home for anything not evidenced enough to sit in a tier.
  flag_id         TEXT NOT NULL,
  tier            TEXT NOT NULL CHECK (tier IN ('A','B','TRACKED')),
  present         INTEGER NOT NULL DEFAULT 1,
  source_turn_id  TEXT,
  source_text     TEXT NOT NULL,
  recorded_at_utc TEXT NOT NULL,
  PRIMARY KEY (subject_id, night_date, flag_id)
);
CREATE INDEX IF NOT EXISTS idx_symptom_recent
  ON symptom_observations(subject_id, night_date DESC);
