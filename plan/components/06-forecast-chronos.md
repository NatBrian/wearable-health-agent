# Component 06. Chronos forecast

**Phase:** A. **Module:** `src/wha/detect/forecast.py`. **Depends on:** 03 features, 04 baseline.

A zero-shot time-series foundation model producing a **second deviation score**. It is **advisory**:
it never sets `level` or `flagged`, it contributes evidence to the belief model, and if it fails
nothing downstream changes.

---

## 1. Why it is here, honestly

Two claims, and they are different.

**Whether it is built** is not in question. It always runs.

**Whether it wins** is a result to report. `research/findings/F4` found the evidence thin: the single
most on-point paper, zero-shot forecasting on consumer wearable data, put Chronos at MASE 0.82
against EWMA at 0.84 at context length 32. That is a 2.4% relative gain over a five-line baseline,
statistically significant and practically almost nothing. Several independent evaluations find
time-series foundation models losing to linear and seasonal-naive baselines.

**So the interesting experiment is not the one the literature already answered.** A rolling median
and MAD baseline needs history, and at five nights MAD frequently collapses to zero on quantised
data, so the band has no width. A zero-shot model carries a prior over short physiological series
and yields a calibrated interval from very few points.

> **The hypothesis: Chronos beats statistics precisely where statistics is weakest, which is the
> cold-start regime this system lives in.** Tested directly on the baseline-age curve from component
> 16. Nobody has published it. If the answer is no, the page says so, and a reported negative result
> is a finding.

---

## 2. The model

`chronos-forecasting >= 2.3`, Apache-2.0. `amazon/chronos-bolt-small`, 47.7M parameters,
`device_map="cpu"`.

Chosen because it is the only family that is simultaneously installable by pip, permissively
licensed, documented for CPU, tolerant of short and variable context, and **NaN-aware by design**
where `torch.nan` is the documented missing marker rather than a hack.

**Context length is a maximum, not a minimum.** Chronos-Bolt accepts up to 2048 and any length below
it. The HRV paper ran at context 32 and got its best result. Do not pad to a fixed size and do not
believe any guidance about needing 512 points; that constraint belongs to other model families and
is the reason two of them were excluded from this project.

Model size is a config value and is **swept in the ablation**, because the published finding is that
size matters less than framing.

---

## 3. Interface

```python
def forecast_night(
    history: Sequence[NightlyFeatures],   # usable nights, oldest first, EXCLUDING tonight
    actual_rhr: float,
) -> Forecast:
    """One-step-ahead forecast of tonight's nocturnal RHR, with an interval."""
```

```
context      = [n.rhr_bpm for n in history]        # NaN for gaps, never imputed
quantiles    = pipeline.predict_quantiles(
                   context=torch.tensor(context),
                   prediction_length=1,
                   quantile_levels=[FORECAST_Q_LO, 0.5, FORECAST_Q_HI])

predicted_bpm = q[0.5]
lo_bpm, hi_bpm = q[FORECAST_Q_LO], q[FORECAST_Q_HI]
half_width    = max((hi_bpm - lo_bpm) / 2, FORECAST_HALF_WIDTH_FLOOR_BPM)
forecast_z    = (actual_rhr - predicted_bpm) / half_width
```

`forecast_z` is the second deviation score: how far tonight fell outside **the model's own
uncertainty**, which is a different quantity from `robust_z` and is the point of having it.

The half-width floor exists for the same reason the MAD floor does. A model that is very confident
on a short flat series can return a near-zero interval and produce an infinite `forecast_z`.

### Gaps are never imputed

Unusable nights enter the context as `NaN`, which Chronos handles natively. **Do not fill them, do
not drop them and close the gap, and do not carry the last value forward.** Dropping a gap silently
changes the spacing of the series and tells the model a lie about the timeline.

---

## 4. Statuses

`Forecast.status` is always set. The forecast is optional in every downstream consumer.

| Status | When | Downstream |
|---|---|---|
| `OK` | A prediction was produced | `forecast_z` is available as evidence |
| `TOO_FEW_NIGHTS` | Fewer than `FORECAST_MIN_NIGHTS` usable nights in the context | No evidence contributed |
| `NOT_RUN` | The `ml` dependency group is not installed, or the forecast is disabled by config | No evidence contributed |
| `FAILED` | The model raised, timed out, or returned a non-finite value | No evidence contributed, one `system_status` row |

**A `FAILED` forecast is not an error path for the batch.** It is caught inside this module, recorded
and returned as a status. The deterministic detector has already run and is unaffected. This is what
"advisory" means in code rather than in prose.

---

## 5. Loading and caching

Model load is the expensive part; inference on 30 points is milliseconds.

- Load **once per process**, cached in a module-level singleton behind a lock.
- Weights cache under `data/model_cache/`, which is gitignored. Roughly 200 MB for `small`.
- First run downloads. **Every dataset-free test must therefore either use `NOT_RUN` or a stubbed
  pipeline.** A unit test must never download a model.
- `wha doctor` reports whether the weights are present, and `wha data fetch chronos` pre-downloads
  them so an unattended run does not stall on a network fetch.

---

## 6. What it must not do

- **Never set `level` or `flagged`.** Enforced by the fact that `detect_night` computes the level
  before calling this module, and by a test.
- Never write to `detections` itself. It returns a `Forecast`; component 05 stores it.
- Never raise into the batch.
- Never be required for an episode to run. Every belief update works with
  `forecast.status != OK`.
- Never be tuned, fine-tuned or trained. Zero-shot only, which is the whole point.

---

## 7. Evidence contribution

`forecast_z` reaches the belief model as **one likelihood factor, behind a config flag**, so the
ablation is clean:

```
FORECAST_AS_EVIDENCE = True   # ablation toggles this
```

It is a second, noisy observation of the same underlying quantity as the residual, so it is given a
**deliberately wide** noise term. Treating it as independent confirmation would double-count the
same night and inflate confidence.

If the ablation shows it contributes nothing, the flag goes to `False` in the reported
configuration and the write-up says so.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| Context shorter than `FORECAST_MIN_NIGHTS` | `TOO_FEW_NIGHTS`. **This is the norm in the first week and is not a failure** |
| Context entirely `NaN` | `TOO_FEW_NIGHTS` |
| Context is constant | Interval may collapse. Half-width floor applies |
| Model returns `NaN` or `inf` | `FAILED`, recorded, never propagated |
| Weights not downloaded, no network | `NOT_RUN`, recorded once per process, not per night |
| `ml` group not installed | `NOT_RUN`. **The import is lazy**, inside the function, so the core has no hard dependency on torch |
| Two threads request the model at once | The load lock serialises them. One load |

---

## 9. Tests

`tests/unit/detect/test_forecast.py`. **No test downloads a model.** A stub pipeline returning fixed
quantiles is injected.

| Test | Asserts |
|---|---|
| `test_too_few_nights_returns_status_not_error` | 4 nights gives `TOO_FEW_NIGHTS`, no exception |
| `test_forecast_z_computed_from_half_width` | Known quantiles give the exact expected z |
| `test_half_width_floor_prevents_infinite_z` | A zero-width interval yields a finite z |
| `test_gaps_passed_as_nan_not_dropped` | Context length equals the calendar span, not the usable count |
| `test_gaps_are_not_imputed` | No interpolated value appears in the context |
| `test_model_failure_returns_failed_status` | A raising stub gives `FAILED`, no exception escapes |
| `test_non_finite_prediction_returns_failed` | |
| `test_forecast_never_sets_level_or_flagged` | Running detection with a stub that would flag leaves `level` from the deterministic rule |
| `test_missing_ml_group_returns_not_run` | Simulated `ImportError` gives `NOT_RUN` |
| `test_model_loaded_once` | Two calls, one load |
| `test_evidence_flag_disables_contribution` | With `FORECAST_AS_EVIDENCE=False` the belief is identical with and without a forecast |

---

## 10. Exit condition

```bash
uv run pytest tests/unit/detect/test_forecast.py -q
uv run wha data fetch chronos && uv run wha nightly --subject demo-illness-onset --date 2026-09-01
```

The second prints a real forecast with its interval alongside the deterministic level, and the level
is unchanged from the run without a forecast.
