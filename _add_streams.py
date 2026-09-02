"""Add ingestion for the three data types the device actually returns.

Verified against the live bridge on 2026-09-02: oxygen_saturation, distance and
total_calories are populated. Respiratory rate and skin temperature are not, so they are
not added here.
"""

import pathlib

# ---------------------------------------------------------------- schema
p = pathlib.Path("src/wha/db/schema.sql")
s = p.read_text(encoding="utf-8")
anchor = """CREATE TABLE IF NOT EXISTS nightly_features ("""
new_tables = """-- Verified present on the device bridge on 2026-09-02. Sparse: oxygen saturation
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

CREATE TABLE IF NOT EXISTS nightly_features ("""
assert s.count(anchor) == 1
p.write_text(s.replace(anchor, new_tables), encoding="utf-8")

# ---------------------------------------------------------------- migration
p = pathlib.Path("src/wha/db/migrations.py")
s = p.read_text(encoding="utf-8")
s = s.replace("DB_VERSION = 2", "DB_VERSION = 3")
p.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------- normalisers
p = pathlib.Path("src/wha/ingest/base.py")
s = p.read_text(encoding="utf-8")

anchor = """@dataclass(frozen=True)
class NormalisedData:"""
dataclasses = '''@dataclass(frozen=True)
class NormalisedOxygenSaturation:
    """A spot blood oxygen reading. The device sends these individually, not as a stream."""

    subject_id: str
    ts_utc: str
    percentage: float
    origin: str | None


@dataclass(frozen=True)
class NormalisedDistance:
    subject_id: str
    start_utc: str
    end_utc: str
    meters: float


@dataclass(frozen=True)
class NormalisedCalories:
    subject_id: str
    start_utc: str
    end_utc: str
    calories_kcal: float


@dataclass(frozen=True)
class NormalisedData:'''
assert s.count(anchor) == 1
s = s.replace(anchor, dataclasses)

anchor = """    exercise_sessions: list[NormalisedExerciseSession]"""
fields = """    exercise_sessions: list[NormalisedExerciseSession]
    oxygen_saturation_samples: list[NormalisedOxygenSaturation] = field(default_factory=list)
    distance_buckets: list[NormalisedDistance] = field(default_factory=list)
    calorie_buckets: list[NormalisedCalories] = field(default_factory=list)"""
assert s.count(anchor) == 1
s = s.replace(anchor, fields)

s = s.replace("from dataclasses import dataclass", "from dataclasses import dataclass, field")

anchor = """    return NormalisedData(
        heart_rate_samples=hr_samples,
        step_buckets=step_buckets,
        sleep_stages=sleep_stages,
        exercise_sessions=exercise_sessions,
    )"""
parsing = '''    # 5. Blood oxygen. Field names taken from the live bridge, not guessed: the payload
    #    key is "oxygen_saturation" and each record carries "percentage" and "time".
    spo2_samples: list[NormalisedOxygenSaturation] = []
    for item in payload.get("oxygen_saturation") or []:
        ts_val = item.get("time")
        pct = item.get("percentage")
        if not ts_val or pct is None:
            continue
        origin = None
        if isinstance(item.get("metadata"), dict):
            origin = item["metadata"].get("data_origin")
        spo2_samples.append(
            NormalisedOxygenSaturation(
                subject_id=subject_id,
                ts_utc=_parse_iso_utc(str(ts_val)),
                percentage=float(pct),
                origin=origin,
            )
        )

    # 6. Distance covered, in daily buckets like steps.
    distance_buckets: list[NormalisedDistance] = []
    for item in payload.get("distance") or []:
        start_val = item.get("start_time")
        end_val = item.get("end_time")
        meters = item.get("meters")
        if not start_val or not end_val or meters is None:
            continue
        distance_buckets.append(
            NormalisedDistance(
                subject_id=subject_id,
                start_utc=_parse_iso_utc(str(start_val)),
                end_utc=_parse_iso_utc(str(end_val)),
                meters=float(meters),
            )
        )

    # 7. Energy expenditure.
    calorie_buckets: list[NormalisedCalories] = []
    for item in payload.get("total_calories") or []:
        start_val = item.get("start_time")
        end_val = item.get("end_time")
        calories = item.get("calories")
        if not start_val or not end_val or calories is None:
            continue
        calorie_buckets.append(
            NormalisedCalories(
                subject_id=subject_id,
                start_utc=_parse_iso_utc(str(start_val)),
                end_utc=_parse_iso_utc(str(end_val)),
                calories_kcal=float(calories),
            )
        )

    return NormalisedData(
        heart_rate_samples=hr_samples,
        step_buckets=step_buckets,
        sleep_stages=sleep_stages,
        exercise_sessions=exercise_sessions,
        oxygen_saturation_samples=spo2_samples,
        distance_buckets=distance_buckets,
        calorie_buckets=calorie_buckets,
    )'''
assert s.count(anchor) == 1
s = s.replace(anchor, parsing)
p.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------- persistence
p = pathlib.Path("src/wha/ingest/store.py")
s = p.read_text(encoding="utf-8")
anchor = """        for slp in norm.sleep_stages:"""
writes = '''        for spo2 in norm.oxygen_saturation_samples:
            conn.execute(
                """
                INSERT OR REPLACE INTO oxygen_saturation_samples (
                    subject_id, ts_utc, percentage, origin
                ) VALUES (?, ?, ?, ?);
                """,
                (spo2.subject_id, spo2.ts_utc, spo2.percentage, spo2.origin),
            )

        for dist in norm.distance_buckets:
            conn.execute(
                """
                INSERT OR REPLACE INTO distance_buckets (
                    subject_id, start_utc, end_utc, meters
                ) VALUES (?, ?, ?, ?);
                """,
                (dist.subject_id, dist.start_utc, dist.end_utc, dist.meters),
            )

        for cal in norm.calorie_buckets:
            conn.execute(
                """
                INSERT OR REPLACE INTO calorie_buckets (
                    subject_id, start_utc, end_utc, calories_kcal
                ) VALUES (?, ?, ?, ?);
                """,
                (cal.subject_id, cal.start_utc, cal.end_utc, cal.calories_kcal),
            )

        for slp in norm.sleep_stages:'''
assert s.count(anchor) == 1
s = s.replace(anchor, writes, 1)
p.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------- delete-all
p = pathlib.Path("src/wha/service/settings.py")
s = p.read_text(encoding="utf-8")
anchor = '                "exercise_sessions",'
assert s.count(anchor) == 1
s = s.replace(
    anchor,
    '                "exercise_sessions",\n'
    '                "oxygen_saturation_samples",\n'
    '                "distance_buckets",\n'
    '                "calorie_buckets",',
)
p.write_text(s, encoding="utf-8")

print("streams added")
