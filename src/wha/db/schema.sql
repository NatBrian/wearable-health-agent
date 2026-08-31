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
  depth_used       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_episodes_subject_state ON episodes(subject_id, state);

CREATE TABLE IF NOT EXISTS beliefs (
  episode_id     TEXT NOT NULL,
  seq            INTEGER NOT NULL,
  ts_utc         TEXT NOT NULL,
  trigger        TEXT NOT NULL,
  marginals_json TEXT NOT NULL,
  p_illness      REAL NOT NULL,
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

CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY
);
