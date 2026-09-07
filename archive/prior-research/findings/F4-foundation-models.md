# F4 — Pretrained Time-Series & Physiological Foundation Models

**Research date:** 2026-08-30
**Scope:** Models usable WITHOUT training our own. Every claim carries a URL. Claims I could not confirm against a primary source are marked **UNVERIFIED**.
**Method:** HuggingFace Hub API (`huggingface.co/api/models/...`), GitHub REST API, PyPI JSON API, raw source/`config.json`/notebook files pulled directly from the repos, plus arXiv abstracts and full texts. Where I read a config or notebook directly, that is stated.

---

## 1. Executive summary

### Should a 2-week project use a TSFM at all?

**Yes — but exactly one of them, for exactly one job, and not the one you would expect.**

**(a) The strong candidate is Chronos-2 / Chronos-Bolt, not MOMENT.** Chronos is the only family in this survey that is genuinely bucket-2 (pip install, load weights, useful output immediately), CPU-supported by explicit documentation, permissively licensed (Apache-2.0), tolerant of short and variable-length context, and NaN-aware by design. Chronos-Bolt-tiny is 8.65M parameters. ([HF API](https://huggingface.co/amazon/chronos-bolt-tiny), [repo](https://github.com/amazon-science/chronos-forecasting))

**(b) The evidence that TSFMs beat classical baselines in our exact regime is real but thin, and the margin is tiny.** The single most on-point paper — [Zero-Shot HRV Forecasting from Consumer Wearables](https://arxiv.org/abs/2607.20027) — found Chronos at MASE 0.82 versus EWMA at 0.84 at context 32. That is a ~2.4% relative improvement over a five-line baseline. It is statistically significant (p<0.001) and practically almost nothing. Meanwhile [several](https://arxiv.org/abs/2502.12944) [independent](https://arxiv.org/abs/2510.00742) evaluations find TSFMs *losing* to linear and seasonal-naive baselines in other domains. **A rolling median + MAD baseline is not a strawman here; it is a live contender that may well win.**

**(c) The "zero-shot anomaly detection" story is substantially weaker than it looks.** MOMENT's headline zero-shot AD number is reported with `adjbestf1` — point-adjusted *best* F1 — which I confirmed by reading [the actual tutorial notebook source](https://github.com/moment-timeseries-foundation-model/moment/blob/main/tutorials/anomaly_detection.ipynb). That metric (i) requires ground-truth labels to pick the threshold, so it is not deployable, and (ii) is the specific metric [Kim et al. (AAAI 2022)](https://cdn.aaai.org/ojs/20680/20680-13-24693-1-2-20220628.pdf) showed **random noise scores ~0.89 on**. Any "our TSFM does great anomaly detection" claim built on adjusted-F1 should be treated as unproven.

**(d) The physiological/wearable foundation models are almost all the wrong shape for this project.** NormWear, PaPaGei and Pulse-PPG consume **raw waveforms at 64–125 Hz** and emit **embeddings requiring a trained downstream head**. That is bucket 3, it needs labelled data we do not have, and it does not apply to nightly-summary metrics at all. Apple's WBM, Google's LSM-2 and Google's SensorFM — the three models actually trained on daily-cadence consumer wearable behaviour, i.e. exactly our data — are all **bucket 5, weights withheld**. *The models that fit our data are unavailable; the models that are available do not fit our data.*

### Recommended posture

Use Chronos-Bolt-tiny/small as **one forecaster among several**, wrapped so its prediction interval yields an anomaly score, and **benchmark it head-to-head against rolling median + MAD and seasonal-naive**. Budget ~4–6 hours. Treat "did the TSFM actually beat the trivial baseline?" as a *finding to report*, not an assumption. Given the HRV paper's 0.02 MASE margin, there is a real chance the honest answer is "no" — and that is a perfectly good course project result, arguably better than an unexamined "we used a foundation model."

**Do not** attempt NormWear, PaPaGei, Pulse-PPG, UniTS, Moirai or Toto-2.0 inside a 45-hour budget. Reasons itemised per model below.

---

## 2. Verification verdict table

| # | Prior claim | Verdict | Evidence |
|---|---|---|---|
| 1a | MOMENT: `pip install momentfm` | **TRUE** | [PyPI momentfm v0.1.4](https://pypi.org/project/momentfm/), requires-python >=3.10 |
| 1b | MOMENT-1-small 38M / base 125M / large 385M | **PARTLY TRUE** | Paper says ~40M/125M/385M ([arXiv 2402.03885](https://arxiv.org/abs/2402.03885)). Actual safetensors totals from HF API: **37,901,512 / 113,481,608 / 346,368,520**. The paper rounds up; real weights are smaller. |
| 1c | MOMENT native zero-shot anomaly detection | **TRUE, with a large caveat** | The [AD tutorial notebook](https://github.com/moment-timeseries-foundation-model/moment/blob/main/tutorials/anomaly_detection.ipynb) contains a working section "4. Zero-Shot Anomaly Detection" using `task_name="reconstruction"`. **But** it scores with `adjbestf1`, an oracle-threshold, label-requiring, known-inflated metric. See §5.3. |
| 1d | MOMENT licence Apache-2.0 | **FALSE — it is MIT** | [HF cardData `license: mit`](https://huggingface.co/AutonLab/MOMENT-1-large); [GitHub API `license.key: mit`](https://api.github.com/repos/moment-timeseries-foundation-model/moment); PyPI licence text is MIT, "Copyright (c) 2024 Auton Lab, Carnegie Mellon University". Practically harmless (MIT is *more* permissive) but the claim was wrong. |
| 1e | MOMENT "context window capped at 512" | **TRUE, but the wording understates it** | It is not a cap, it is a **fixed** length. Paper: *"we restrict MOMENT's input to a univariate time series of a fixed length T = 512"* and *"we sub-sample longer time series, and pad shorter ones with zeros on the left."* Confirmed in [`config.json`](https://huggingface.co/AutonLab/MOMENT-1-large/raw/main/config.json): `"seq_len": 512, "patch_len": 8, "patch_stride_len": 8`. |
| 2a | Chronos-Bolt: `pip install chronos-forecasting` | **TRUE** | [PyPI chronos-forecasting v2.3.1](https://pypi.org/project/chronos-forecasting/), published 2026-07-02 |
| 2b | chronos-bolt-tiny 9M / mini 21M / base 200M | **TRUE (rounded)** | HF safetensors totals: tiny **8,652,672**; mini **21,236,096**; small **47,718,016**; base **205,292,928** |
| 2c | Chronos-Bolt "<15ms on CPU" | **UNVERIFIED — no source found** | The [AWS blog](https://aws.amazon.com/blogs/machine-learning/fast-and-accurate-zero-shot-forecasting-with-chronos-bolt-and-autogluon/) states only that the models *"can also be used on the CPU"* and gives **no CPU timings**. All published speed numbers are GPU. Treat <15ms as unsourced. |
| 2d | "250x faster than original Chronos" | **TRUE as Amazon states it, but it is a GPU claim** | README: *"up to 250 times faster and 20 times more memory-efficient than the original Chronos models of the same size."* Conditions: 1024 series, context 512, horizon 64, on GPU. |
| 3a | TimesFM: `pip install timesfm` | **TRUE, but use the extra** | [PyPI timesfm v3.0.0](https://pypi.org/project/timesfm/), published **2026-08-28** (two days ago). Bare install pulls only numpy/hf-hub/safetensors. **`pip install timesfm[torch]`** adds torch only. **`timesfm[flax]` and `timesfm[xreg]` pull `jax[cuda]`** — avoid on a CPU laptop. Verified from PyPI `requires_dist`. |
| 3b | `google/timesfm-1.0-200m`, Apache-2.0 | **TRUE but badly out of date** | v1.0 is Apache-2.0 and still up, but last modified **2024-05-17**, 492 downloads. Current line is TimesFM **2.5** / **3.0**. |
| 3c | TimesFM "~800MB, 100-300ms CPU" | **UNVERIFIED** | No primary source found for either figure. Verified parameter counts: 2.0-500m = 498,828,960; 2.5-200m = 231,289,280; 3.0 = 330,710,976. At fp32, 2.0-500m is ~2.0 GB, not 800 MB. |
| 3d | *(not previously claimed)* **TimesFM 3.0 is NON-COMMERCIAL** | **NEW, IMPORTANT** | [HF API for `google/timesfm-3.0-pytorch`](https://huggingface.co/google/timesfm-3.0-pytorch) returns `license: "other"`, `license_name: "timesfm-non-commercial-license-v1.0"`. TimesFM **2.5** remains `apache-2.0`. The newest, best TimesFM is not open-licensed. |
| 4a | NormWear on HF as `mosaic-laboratory/normwear` and `normwear2` | **TRUE** | [normwear](https://huggingface.co/mosaic-laboratory/normwear) (22 downloads, 2 likes); [normwear2](https://huggingface.co/mosaic-laboratory/normwear2) (100 downloads, last modified 2026-08-29 — one day ago) |
| 4b | NormWear 85–110M params | **FALSE** | HF safetensors total for `mosaic-laboratory/normwear` = **193,812,170** (~194M), roughly double the claim. `normwear2` exposes no safetensors total. |
| 4c | GitHub `Mobile-Sensing-and-UbiComp-Laboratory/NormWear`, no pip package | **TRUE** | [Repo](https://github.com/Mobile-Sensing-and-UbiComp-Laboratory/NormWear): Apache-2.0, 63 stars, 5 open issues, last push 2026-04-27. `pip install normwear` → **404, not on PyPI**. Install is `git clone` + `dependencies.txt`. |
| 5 | UniTS open on GitHub (mims-harvard), Tier 2 research artifact | **TRUE, and now stale** | [mims-harvard/UniTS](https://github.com/mims-harvard/UniTS): MIT, 647 stars, 28 open issues, **last push 2024-09-26** — ~23 months stale as of today. No pip package; needs `requirements.txt`, `download_data_all.sh`, YAML task configs and bash launch scripts. Bucket 4 confirmed. |
| 6 | HeartBEiT weights are withheld | **TRUE** | HF search for "heartbeit" returns **zero models**. Multiple secondary sources confirm weights and pretraining data are not public. Paper: [arXiv 2212.14040](https://arxiv.org/abs/2212.14040). Contrast [wanglab/ecg-fm](https://huggingface.co/wanglab/ecg-fm), which *is* released. |
| 7 | "AI on the Pulse used UniTS and got +22% F1 over 12 baselines" | **TRUE on the numbers, MISLEADING on the setup** | [arXiv 2508.03436](https://arxiv.org/abs/2508.03436), CIKM'25. The ~22% F1 gain and 12 baselines are real. **But** UniTS was **fine-tuned, not zero-shot**: *"we split each series 80:20 for train/test, trained for 20 epochs, and report the F1 score averaged over 5-fold CV"*, plus per-patient fine-tuning *"for 2 epochs with windows of 16 samples."* All 12 baselines are deep-learning AD models (LSTM-NDT, MSCRED, HypAD, TranAD, OmniAnomaly, MTAD-GAT, CAE-M, MAD-GAN, TadGAN, USAD, GDN, DAGMM) — **not one simple statistical baseline was tested**. Data is 10-second-resolution HR/HRV from WESAD/DREAMER/HCI plus a 6-patient in-house set at 1-minute resolution — **not daily wearable summaries**. |

---

## 3. THE AVAILABILITY TABLE

Buckets: **1** = callable API · **2** = pretrained + true zero-shot · **3** = pretrained but needs head/fine-tuning · **4** = research code, technically reusable · **5** = weights withheld.

"Min context" = shortest input the model accepts. "Hrs to output" is **my estimate** for a competent Python developer on a CPU-only Windows laptop running Python 3.11.9 (the machine this research was run on), starting from zero.

| Model | Bucket | Install | HF / repo id (params) | Licence | CPU? | Min context | Handles gaps? | Channel-independent? | Hrs to output |
|---|---|---|---|---|---|---|---|---|---|
| **Chronos-2** | **2** | `pip install "chronos-forecasting>=2.0"` | `amazon/chronos-2` (119,477,664) | Apache-2.0 | **Yes**, `device_map="cpu"` documented | Any; max **8192** | **Yes** — NaN is the documented missing/pad marker | **Joint** (group attention over variates) | **3–5** |
| **Chronos-Bolt** | **2** | `pip install chronos-forecasting` | `amazon/chronos-bolt-{tiny,mini,small,base}` (8.65M/21.2M/47.7M/205.3M) | Apache-2.0 | **Yes** (AWS blog) | Any; max **2048** | Yes (NaN left-pad) | Channel-independent | **2–4** |
| **Chronos-T5** (original) | 2 | `pip install chronos-forecasting` | `amazon/chronos-t5-{tiny..large}` (small = 46,154,240) | Apache-2.0 | Yes but slow (sampling-based) | Any; max **512** | Yes | Channel-independent | 3–5 |
| **MOMENT** | **2** (recon/forecast) / 3 (classification) | `pip install momentfm` | `AutonLab/MOMENT-1-{small,base,large}` (37.9M/113.5M/346.4M) | **MIT** | Yes — `config.json` default `"device": "cpu"` | **Fixed 512** (left zero-pad if shorter) | **Yes** — explicit `input_mask` and `mask` args | Channel-independent | **5–8** (dep pins, §4.3) |
| **TimesFM 2.5** | **2** | `pip install timesfm[torch]` | `google/timesfm-2.5-200m-pytorch` (231,289,280) | Apache-2.0 | Yes (torch extra avoids jax) | Any; max **16k** | Partial (padding mask) | Channel-independent | 3–5 |
| **TimesFM 3.0** | 2 (**licence-blocked**) | `pip install timesfm[torch]` | `google/timesfm-3.0-pytorch` (330,710,976) | **timesfm-non-commercial-v1.0** | Yes | Any | Yes | **Joint** multivariate | 3–5 |
| **TTM / Tiny Time Mixers** | **2** | `pip install granite-tsfm` | `ibm-granite/granite-timeseries-ttm-r2` (**805,280**) | Apache-2.0 | **Yes, explicitly designed for it** | **Hard min 512** (or 1024/1536 branches) | Weak — no native missing-value path | Both modes (channel-mixing available) | 4–7 (needs py>=3.11, torch>=2.10) |
| **Moirai / Moirai-MoE** | 2 (**licence-restricted**) | `pip install uni2ts` | `Salesforce/moirai-1.1-R-large` (310,970,624); `moirai-moe-1.0-R-base` (935,361,504); `moirai-1.0-R-small` (13,827,528) | **CC-BY-NC-4.0** | Yes | Any | Yes | **Joint** (any-variate attention) | 6–10 (pins `torch<2.5`, `datasets~=2.17`) |
| **Toto (Open-Base-1.0)** | 2 | `pip install toto-ts` | `Datadog/Toto-Open-Base-1.0` (151,306,080) | Apache-2.0 | Degraded (Ampere GPU recommended) | ~512 typical | Yes | **Joint** (time/variate attention) | 6–10 |
| **Toto 2.0** | 2 (**blocked here**) | `pip install toto-models` | `Datadog/Toto-2.0-{4m,22m,313m,1B,2.5B}` (4.14M/21.9M/312.7M/…) | Apache-2.0 | Degraded | 512 | **Yes — explicit `target_mask`** | Joint | **Blocked: requires Python >=3.12; local env is 3.11.9** |
| **TabPFN-TS** | 2 (partly **1** — optional remote inference) | `pip install tabpfn-time-series` | `PriorLabs/tabpfn-time-series` (~11M) | Apache-2.0 (client can call remote API) | Yes | Any (tabular featurisation) | Yes (missing rows simply absent) | Both | 4–6 |
| **Lag-Llama** | 4 | git clone (**not on PyPI**) | `time-series-foundation-models/Lag-Llama` (**2,449,299**) | Apache-2.0 | Yes | Trained at **32** | Weak | Channel-independent | 6–10 (unmaintained since 2024) |
| **UniTS** | **4** | git clone + `requirements.txt` + `download_data_all.sh` | `mims-harvard/UniTS` (weights in GH Releases) | MIT | Yes | Task-config dependent | Not documented | Joint-ish | **15–25** |
| **TimeGPT** | **1** | `pip install nixtla` | api.nixtla.io | Commercial, closed | N/A (remote) | Any | Yes | Both | 1–2 (+API key; **pricing pages 404 — cost UNVERIFIED**) |
| **PatchTST** | 3 | `transformers` / `granite-tsfm` | `ibm/patchtst-*` | Apache-2.0 | Yes | 512 typical | No | Channel-independent | Not a foundation model — trains per dataset |
| **NormWear** | **3** | **git clone only** (not on PyPI) | `mosaic-laboratory/normwear` (**193,812,170**) | Apache-2.0 | Yes (example uses `torch.device('cpu')`) | e.g. 128 samples @64 Hz | Not documented | Multivariate embeddings | **12–20** — and see §4.14 |
| **NormWear2** | 3/4 | git clone | `mosaic-laboratory/normwear2` | Apache-2.0 | Yes | window 4096, `nvar` 10 | Not documented | Joint world-model | 15–25 |
| **PaPaGei** | **3** | conda + `requirements.txt` + `pyPPG==1.0.41` | GitHub Nokia-Bell-Labs; weights on **Zenodo 13983110** | **BSD-3-Clause** | Yes | **10 s @125 Hz = 1250 samples** | N/A (waveform) | 512-d embeddings | 10–16 |
| **Pulse-PPG** | **3** | git clone | `maxxu05/pulseppg`; weights Zenodo **10.5281/zenodo.17270930** | see repo | Yes | **4-minute raw PPG segments** | N/A | Embeddings | 10–16 |
| **Apple WBM** | **5** | — | — | — | — | 27 daily behavioural metrics | — | — | **Not available** |
| **Google LSM-2** | **5** | — | — | — | — | Day-long minute-level windows | AIM masking (internal) | — | **Not available** |
| **Google SensorFM** | **5** | — | — | — | — | 34 one-minute features | — | — | **Not available** |
| **HeartBEiT** | **5** | — | — | — | — | 12-lead ECG images | — | — | **Not available** |
| **ECG-FM** | 3 | git clone | `wanglab/ecg-fm` | see repo | Yes | 12-lead ECG @500 Hz | N/A | — | Irrelevant to consumer wearables |
| **SleepFM** | 3/4 | via `braindecode` | `braindecode/SleepFM`, `braindecode/SleepFMStager` (community ports; 20 and 17 downloads) | see repo | Yes | PSG epochs (EEG/EOG/EMG) | N/A | Multimodal | Irrelevant — needs polysomnography, not a wrist wearable |

---

## 4. Per-model writeups (A–Q)

### 4.1 Chronos-2 — the recommendation

- **A. Task.** Probabilistic forecasting: univariate, multivariate, and covariate-informed, all zero-shot.
- **B. Input.** Max context **8192**, `input_patch_size` 16 — read directly from [`config.json`](https://huggingface.co/amazon/chronos-2/raw/main/config.json). Accepts a `(batch, n_variates, length)` numpy array, or a list of dicts with `target`/`past_covariates`/`future_covariates`, or a pandas DataFrame via `predict_df`. **No minimum context and no mandatory normalisation** — the pipeline scales internally.
- **C. Pretraining data.** Real + synthetic corpora, including *"synthetic datasets that impose diverse multivariate structures on univariate series"* ([tech report, arXiv 2510.15821](https://arxiv.org/abs/2510.15821)). **No physiological/wearable data disclosed.**
- **D. Architecture.** Encoder-only T5-style, `d_model` 768, 12 layers, **119,477,664 params**, with a **group attention** mechanism enabling in-context learning across a group of series.
- **E. Tasks.** Forecasting (point + quantile). Not natively anomaly detection, imputation, or classification.
- **F. Zero-shot — verified how?** Working quickstart notebook read directly from the repo: `pipeline.predict_quantiles(np.random.randn(32, 3, 512), prediction_length=48, quantile_levels=[0.1,0.5,0.9])`. No training step anywhere. **Genuine bucket 2.**
- **G. Bucket 2.** Evidence: notebook above + `pip install "chronos-forecasting>=2.0"` on PyPI.
- **H.** `pip install "chronos-forecasting>=2.0"`; id `amazon/chronos-2`. Mirror at `autogluon/chronos-2` (identical param count); smaller `autogluon/chronos-2-small` (28M).
- **I. Licence.** Apache-2.0 — clean, commercial-safe.
- **J. Hardware.** Quickstart comment, verbatim: *"GPU recommended for faster inference, but CPU is also supported using `device_map='cpu'`."* Amazon reports *"over 300 time series forecasts per second on a single A10G GPU"*. **No published CPU latency.** ~480 MB fp32 weights.
- **K. Missing data.** Good. `torch.nan` is the documented marker — base docstring: *"use left-padding with `torch.nan` to align series of different lengths"*, and the Chronos-2 pipeline uses `torch.isnan(...)` internally to route around unknown covariate values. Gappy input is a first-class case, not a hack.
- **L. Multivariate.** **Joint**, via group attention across variates — one of only three models here (with Moirai and Toto) that can learn cross-channel structure.
- **M. Circadian structure.** 8192 context is ample at any wearable cadence; no explicit seasonality module, structure is learned.
- **N. Benchmarks.** SOTA zero-shot on fev-bench, GIFT-Eval and Chronos Benchmark II; *"win rate of over 90% against Chronos-Bolt in head-to-head comparisons."*
- **O. Limitations.** No physiological pretraining. Not an anomaly detector out of the box — you must build the residual/interval scoring yourself. Susceptible to the leakage critique in §5.5.
- **P. Repo health.** [5,776 stars, 36 open issues, last push 2026-08-14](https://api.github.com/repos/amazon-science/chronos-forecasting). `amazon/chronos-2` has **29,603,437 downloads**. Healthiest repo in this survey by a wide margin.
- **Q. Lesson.** In-context learning over a *group* of series is how you get multivariate and covariate support without per-dataset training. That is the architectural idea worth stealing.

### 4.2 Chronos-Bolt — the pragmatic choice

- **A–B.** Direct multi-step quantile forecasting. Context **2048**, `input_patch_size` 16, `prediction_length` 64 (from `config.json`).
- **D.** T5 encoder-decoder, patch-based. tiny **8,652,672** / mini **21,236,096** / small **47,718,016** / base **205,292,928**.
- **F/G. Bucket 2**, verified by PyPI package + README quickstart.
- **I.** Apache-2.0. **J.** CPU supported (AWS blog); tiny is ~35 MB fp32 — trivially laptop-friendly. **CPU latency unpublished.**
- **K.** NaN left-padding. **L.** Channel-independent — cannot learn HR↔HRV↔sleep coupling.
- **N.** 5% lower error than original Chronos, 250x faster, 20x more memory-efficient (GPU conditions).
- **P.** Same healthy repo. `amazon/chronos-bolt-base` 1,243,025 downloads; `chronos-bolt-small` 6,933,938.
- **Q.** Patching + direct multi-step decoding is where the 250x came from — autoregressive token sampling was the bottleneck, not model size.

### 4.3 MOMENT — usable, but read the caveats

- **A.** General-purpose TS model: forecasting, classification, anomaly detection, imputation, embeddings.
- **B. Input — the key constraint.** `x_enc` of shape `[batch, n_channels, 512]`. **Fixed** T=512. Paper: *"we sub-sample longer time series, and pad shorter ones with zeros on the left."* Two optional masks: `input_mask` (which timesteps to attend to — use this for padding) and `mask` (unobserved values).
- **C.** The "Time Series Pile": Informer datasets, Monash archive, UCR classification archive, TSB-UAD. **Almost no medical/wearable data** — an "ECG" category in UCR and "the human body" as one anomaly source. No consumer wearable data.
- **D.** T5-encoder (`flan-t5-large` backbone for the large variant), `d_model` 1024, 24 layers, patch_len 8 → 64 patches. 37.9M / 113.5M / 346.4M actual.
- **E.** All five task heads. **F.** Zero-shot reconstruction/AD verified in the tutorial notebook (see §5.3 for what the numbers actually mean).
- **G. Bucket 2** for reconstruction/imputation/AD; **bucket 3** for classification (needs a head).
- **H.** `pip install momentfm`; `AutonLab/MOMENT-1-{small,base,large}`.
- **I. MIT** (not Apache — prior claim wrong).
- **J.** `config.json` ships `"device": "cpu"`. The tutorial itself calls `.to("cuda")` but that is trivially changed. Small variant is ~150 MB fp32.
- **K. Best-in-class gap handling in principle** — the mask arguments are exactly what gappy wearable data needs, and pretraining was masked-patch reconstruction, so missingness is in-distribution.
- **L.** Channel-independent. **M.** 512 fixed; see §6 for what that means per cadence.
- **N.** *"Better than all baselines"* zero-shot on AD; best F1 with linear probing. Metric is adjusted-F1 over 44 UCR series — see §5.3.
- **O. Two serious failure modes.** (1) Authors' own words: MOMENT *"struggles to differentiate between vertically shifted time series as it normalizes signals prior to modeling."* **For an early-warning system this is close to disqualifying** — a sustained elevation in resting heart rate *is* a vertical shift, and it is precisely the signal we want. (2) Authors caution: *"it's important to use its predictions with care, especially in high-stakes settings like healthcare."*
- **P.** 833 stars, 21 open issues, last push 2026-02-10 — maintained but slowing. **Dependency landmine:** `momentfm` pins **exact** versions — `huggingface-hub==0.24.0`, `numpy==1.25.2`, `transformers==4.33.3`. transformers 4.33.3 is from 2023. This will fight any other modern ML package; budget a dedicated venv and expect resolver pain. This is the main reason for the 5–8h estimate versus Chronos's 2–4h.
- **Q.** Masked-patch reconstruction pretraining gives you imputation and anomaly detection for free from a single objective — elegant. But normalising away level information costs you exactly the anomalies clinicians care about.

### 4.4 TimesFM 2.5 / 3.0

- **B.** 2.5: 16k max context; frequency indicator removed (was required in 1.0/2.0); optional 30M quantile head, horizons to 1k.
- **D.** 2.0-500m = 498,828,960; **2.5-200m = 231,289,280**; **3.0 = 330,710,976**.
- **G/H. Bucket 2.** `pip install timesfm[torch]`. **Critical install detail:** the `flax` and `xreg` extras pull `jax[cuda]`; the `torch` extra pulls only `torch>=2.0.0`. On a CPU laptop use `[torch]`.
- **I. Licence is the story.** 1.0/2.0/2.5 = Apache-2.0. **3.0 = `timesfm-non-commercial-license-v1.0`.** Verified via HF API `license_name`. Use 2.5 if the licence matters.
- **L.** 2.5 channel-independent; **3.0 adds native multivariate + covariates**, but under the restrictive licence.
- **N.** Per GIFT-Eval commentary, TimesFM-2.5 is one of only two models (with Chronos-2) reported to beat AutoTheta at second-level frequency.
- **P.** [28,314 stars, 224 open issues, last push 2026-08-28](https://api.github.com/repos/google-research/timesfm) — very active. Note `google/timesfm-1.0-200m` shows only 492 downloads: the old checkpoint the prior research recommended is effectively abandoned.
- **Q.** Google moved from Apache to a bespoke non-commercial licence at v3.0. Pin your version and read the licence at pin time; do not assume the family licence.

### 4.5 TTM / Tiny Time Mixers (IBM)

- **D. 805,280 parameters** (verified via HF API on both r1 and r2). By far the smallest real TSFM here — three orders of magnitude below Chronos-2.
- **B. The blocker: hard minimum context of 512** (or 1024/1536 depending on branch). Model branches are named `<context>-<prediction>-[ft]-[mae]-[r2/r2.1]`, e.g. `512-96-r2`. Unlike Chronos, you cannot feed it 60 points.
- **G/H. Bucket 2.** `pip install granite-tsfm`; `ibm-granite/granite-timeseries-ttm-r2`; card says *"directly apply the pre-trained model on your target data to get an initial forecast (with no training)."*
- **I.** Apache-2.0. **J.** *"extremely small and fast"*, *"can be executed even on CPU-only machines"* — the strongest explicit CPU claim of any model surveyed, though again with no published millisecond figures.
- **K.** Weak — no documented missing-value path. You must impute first.
- **L.** Supports both channel-independence and **channel-mixing**, plus exogenous and static categorical infusion.
- **P.** [884 stars, only 5 open issues, last push 2026-08-28](https://api.github.com/repos/ibm-granite/granite-tsfm) — cleanest issue tracker in the survey. But `granite-tsfm` v0.3.9 requires **python >=3.11,<3.14 and torch>=2.10** and declares 35 dependencies.
- **Q.** An MLP-mixer at 0.8M params competing with 200M transformers is the strongest evidence in this whole survey that **scale is not the active ingredient for time series**. If a 0.8M model matches a 200M one, the task has limited learnable structure — which is exactly the §5 argument.

### 4.6 Moirai / Moirai-MoE (Salesforce)

- **I. Licence is disqualifying for anything commercial: `cc-by-nc-4.0`.** Verified on all four checkpoints. Card adds: *"for research purposes only."* Fine for an assessed course project, not for anything beyond.
- **D.** `moirai-1.0-R-small` 13,827,528; `moirai-1.1-R-large` 310,970,624; `moirai-moe-1.0-R-small` 117,099,528; `moirai-moe-1.0-R-base` 935,361,504.
- **L.** **Joint** — any-variate attention flattens variates into the sequence, so cross-channel structure is learnable. Architecturally attractive for HR/HRV/sleep/steps.
- **H.** `pip install uni2ts`. **P.** [1,580 stars, 49 open issues, last push 2026-06-02](https://api.github.com/repos/SalesforceAIResearch/uni2ts). Install friction is real: pins `torch<2.5,>=2.1`, `datasets~=2.17.1`, `numpy~=1.26.0`, `gluonts~=0.14.3`, plus `hydra-core` config machinery.
- **N.** In the HRV wearable study, **MOIRAI was the worst of the three TSFMs** (MASE 0.87 at ctx 32, tying the naive Mean baseline).
- **Q.** Any-variate attention is the cleanest published answer to "how do you make one model handle arbitrary channel counts."

### 4.7 Toto (Datadog)

- **D.** `Toto-Open-Base-1.0` = 151,306,080. **Toto 2.0** family: 4,144,448 / 21,915,584 / 312,684,608 / 1B / 2.5B, all Apache-2.0, released 2026-06-04.
- **K. Notable:** Toto 2.0's forecast call takes an explicit **`target_mask`** alongside `target` — first-class missingness. Flash Attention is only enabled *"when the context has no missing values"*, implying a correct-but-slower masked path otherwise.
- **L.** Joint, via alternating time/variate attention.
- **J/H. The practical blocker:** `pip install toto-models` requires **Python >=3.12**; the local environment is **3.11.9**. The older `toto-ts` v0.2.0 works on 3.10+ but pins `torch==2.7.0` exactly. Docs recommend *"CUDA-capable device (Ampere generation or newer)"*.
- **P.** [538 stars, 25 open issues, last push 2026-08-25](https://api.github.com/repos/DataDog/toto) — healthy.
- **Q.** Toto exists because Datadog found general TSFMs underperformed on observability data (see §5.4) — a direct demonstration that domain shift beats scale.

### 4.8 TabPFN-TS

- **A/D.** Reframes forecasting as tabular regression: featurise timestamps, then apply the pretrained TabPFN-v2 prior-fitted network. **~11M parameters**, no time-series-specific pretraining at all.
- **N.** Ranked **1st on GIFT-Eval**; SOTA on covariate-informed forecasting on fev-bench.
- **H/I.** `pip install tabpfn-time-series` (v1.2.0). Apache-2.0, but depends on `tabpfn-client` — some paths call a **remote** PriorLabs API, making it partly bucket 1. Check which backend you get.
- **Q. The most damaging result in this survey for the TSFM thesis.** An 11M-parameter model with **zero time-series pretraining** tops the main TSFM benchmark. If that is true, the value is in the tabular prior and the featurisation, not in "foundation models for time series."

### 4.9 Lag-Llama

- **D. 2,449,299 parameters** — tiny. Trained at **context 32**.
- **G. Bucket 4.** Not on PyPI (`pip install lag-llama` → 404); git clone + Colab demos. Apache-2.0.
- **P.** [1,601 stars but 66 open issues and last push 2025-06-06](https://api.github.com/repos/time-series-foundation-models/lag-llama); HF repo last modified 2024-05-14. Effectively unmaintained. Historically important as "the first open-source TS foundation model"; superseded on every axis.

### 4.10 UniTS

- Covered in §2 row 5. **Bucket 4.** MIT, weights in GitHub Releases (tag `ckpt`), no pip package. Supports forecasting/classification/AD/imputation with prompt tuning; zero-shot is limited to *new forecasting lengths* and *new datasets via a specialised variant* — **anomaly detection is not zero-shot in the standard flow**.
- **Last push 2024-09-26.** 15–25h estimate reflects `download_data_all.sh` (pulls the full multi-task dataset suite), YAML task configs, and bash launch scripts, on a two-year-old dependency set.
- The "AI on the Pulse" result that made UniTS look attractive is a **fine-tuned** result (§2 row 7), so it does not transfer to a zero-shot plan.

### 4.11 TimeGPT (Nixtla)

- **Bucket 1.** `pip install nixtla` (v0.8.0, 2026-07-21), Apache-2.0 client against a closed commercial endpoint.
- **Cost: UNVERIFIED.** `nixtla.io/pricing`, `nixtla.io/pricing-plans` and `docs.nixtla.io/docs/getting-started-pricing_plans` all returned **404** at time of research. Do not budget against a remembered price.
- **Disqualifier for this project regardless of price:** sending participant physiological data to a third-party US API is a data-governance problem an AI-in-Healthcare course project should not create. Flag this in the report rather than doing it.

### 4.12 PatchTST / HF time-series family

- Not foundation models. `PatchTSTForPrediction`/`PatchTSMixer` in `transformers` ship **architectures, not general pretrained weights** — you train per dataset. **Bucket 3** at best; for our purposes treat as "train your own", i.e. out of scope. Its lasting contribution is the patching + channel-independence recipe that MOMENT, Chronos-Bolt, TimesFM and TTM all inherited.

### 4.13 NormWear / NormWear2

- **A.** *"A Foundation Model for Multivariate Wearable Sensing of Physiological Signals"* — pretrained on PPG, ECG, EEG, GSR and IMU.
- **B. The decisive mismatch.** Input is `[batch, channels, seq_len]` of **raw waveform**; the README example is `torch.rand(2, 3, 64*2)` at `sampling_rate=64` — a 2-second window at 64 Hz. NormWear2 uses window 4096 with `nvar=10`. **Nothing in this model consumes a nightly summary metric.** If our data is one RHR value per night, NormWear is not applicable at any effort level.
- **E/F. Output is embeddings**: `[batch, channels, patches, 768]` from `model.get_embedding(...)`. A classifier head must be trained downstream. There is a text–signal alignment path claimed for zero-shot on unseen tasks, but the documented main path is embeddings + head.
- **G. Bucket 3.**
- **D/H.** **193,812,170 params** (HF safetensors). No pip package; `git clone` + `dependencies.txt` + a checkpoint from GitHub Releases `v1.0.0-alpha` or HF `mosaic-laboratory/normwear`.
- **I.** Apache-2.0. **J.** CPU example provided.
- **P.** 63 stars, 5 open issues, last push 2026-04-27. `normwear` HF repo: **22 downloads**. This is a low-adoption research artifact — you would be among the first outside users, with no Stack Overflow safety net. Hence 12–20h.
- **NormWear2** (HF updated **2026-08-29**, one day before this research) is a *world model* — `model.predict(x[:, :128, :], 64)` forecasts future physiological signals across scales "from raw waveform to day-level patterns". Paper [arXiv 2605.15465](https://arxiv.org/abs/2605.15465). Conceptually the closest thing to what this project wants, but brand-new, undocumented, and unproven.

### 4.14 PaPaGei (Nokia Bell Labs) and Pulse-PPG

- **PaPaGei** ([ICLR'25](https://github.com/Nokia-Bell-Labs/papagei-foundation-model)): input is **10-second PPG segments resampled to 125 Hz (1250 samples)**, bandpass-filtered. Output is a **512-d embedding**; you fit a linear model or shallow net on top. **Bucket 3.** Weights ungated on **Zenodo record 13983110**. **BSD-3-Clause** — commercially usable. 176 stars, 5 open issues, last push 2025-07-08. Evaluated on 20 tasks across 10 datasets.
- **Pulse-PPG** ([UbiComp'25, arXiv 2502.01108](https://arxiv.org/abs/2502.01108)): first PPG FM trained **exclusively on raw field PPG** — 21 billion points, 120 participants, 100 days, 822,247 four-minute segments. Weights on Zenodo **10.5281/zenodo.17270930**. **Bucket 3.**
- **Both require raw PPG waveforms.** Consumer wearable APIs (Fitbit, Apple Health, Garmin, Oura) **do not export raw PPG** — they export derived metrics. Unless the project has raw waveform access, both models are inapplicable regardless of quality.
- A useful independent check exists: [Benchmarking Open-Source PPG Foundation Models for Biological Age Prediction](https://github.com/Misterbra/ppg-age-benchmark) compares Pulse-PPG and PaPaGei-S head to head.

### 4.15 Apple WBM, Google LSM-2, Google SensorFM — bucket 5, and the most painful finding

These are the only three models pretrained on exactly our data type, and none of them is available.

- **Apple Wearable Behavior Model (WBM)** — [arXiv 2507.00191](https://arxiv.org/abs/2507.00191). Trained on **2.5 billion hours** from **161,855 participants** in the Apple Heart and Movement Study. Input is **27 human-interpretable daily behavioural metrics** (active energy, walking pace, HRV, respiratory rate, sleep duration…), patched through **Mamba-2**. Evaluated on 57 health tasks; beat sensor-based (PPG) models on nearly all *dynamic* tasks (pregnancy, sleep quality, respiratory infection); 92% AUC on pregnancy detection when fused with PPG. **No weights, no API.**
- **Google LSM-2 with Adaptive and Inherited Masking (AIM)** — [arXiv 2506.05321](https://arxiv.org/abs/2506.05321), [Google blog](https://research.google/blog/lsm-2-learning-from-incomplete-wearable-sensor-data/). 40 million hours of day-long multimodal sensor data. AIM *"treats missingness as a natural artifact of real-world data rather than erroneous measures that must be filled in"*, using learnable mask tokens for both inherited and artificial missingness. **No weights.**
- **Google SensorFM** — [Google blog](https://research.google/blog/sensorfm-towards-a-general-intelligence-and-interface-for-wearable-health-data/). SensorFM-B = **100M params**, over **one trillion minutes** from **5 million people**, 20+ Fitbit/Pixel Watch models, 34 one-minute aggregate features from PPG/accelerometry/EDA/skin temperature/altimetry, 35 downstream health tasks. **No availability statement of any kind on the release blog.**

**Architectural lesson (Q), and it is the most useful takeaway in this document:** Apple's headline result is that a model over **derived daily behavioural metrics beat a model over raw PPG sensor streams** on most dynamic health tasks. That is direct, large-scale validation that the *metric-level* representation this project is forced into by consumer API constraints is not a compromise — it may be the better representation. Google's AIM is likewise a validation that **explicit missingness modelling, not imputation**, is the right way to handle gappy wearable data. We can adopt both ideas without their weights.

### 4.16 ECG / sleep models — confirmed irrelevant

Confirmed as instructed. **HeartBEiT: weights withheld (bucket 5)** — no HF repo exists. **ECG-FM** ([wanglab/ecg-fm](https://huggingface.co/wanglab/ecg-fm)) and **ECGFounder** *are* released, but need **12-lead clinical ECG at ~500 Hz**. **SleepFM** exists only as community `braindecode` ports (`braindecode/SleepFM`, 20 downloads) and needs **polysomnography** (EEG/EOG/EMG). Consumer wrist wearables produce none of these inputs. **Confirmed irrelevant — do not spend time here.**

---

## 5. Evidence on TSFM versus classical baselines (the critical question)

### 5.1 The one directly on-point positive result — and its real size

**[Zero-Shot Heart Rate Variability Forecasting from Consumer Wearables Using Time Series Foundation Models](https://arxiv.org/abs/2607.20027)** is the closest published match to this project's regime.

- Device: Samsung Galaxy Watch Active 2 (PPG). n=49 healthy individuals, four weeks, *"highly fragmented real-world patterns"*.
- Metric: RMSSD from 5-minute PPG segments. Context **32 (2.7 h)** and **64 (5.3 h)**. Horizon 1–24 steps.
- Models: TimesFM-1.0-200m, Chronos-bolt-base, MOIRAI-1.0-R-base — **no fine-tuning**.
- Baselines: Mean, ETS (additive damped trend), **EWMA (α=0.3)**.

| Model | MASE @ ctx 32 | MASE @ ctx 64 |
|---|---|---|
| Chronos-bolt-base | **0.82** | 0.82 |
| TimesFM | 0.84 | **0.81** |
| **EWMA (α=0.3)** | **0.84** | **0.84** |
| Mean | 0.87 | 0.85 |
| MOIRAI | 0.87 | 0.85 |
| ETS | 0.95 | 0.86 |

**Read this table honestly.** The paper's conclusion — *"foundation models outperform traditional baselines"*, with *"Chronos outperforms EWMA across both contexts (p<0.001)"* — is correct. But the effect is **0.02 MASE, ~2.4% relative**, against a one-line EWMA. A 205M-parameter model bought a 2% improvement over `pandas.Series.ewm()`. And the paper's own recommendation hedges: TSFMs are viable *"with domain-specific fine-tuning."*

**Two secondary findings that matter more than the headline:**
1. **Context 32 and 64 worked.** This is the strongest available evidence that Chronos-family models are usable at short wearable context lengths, and it directly contradicts any "you need 512 points" framing.
2. **MOIRAI tied the naive Mean baseline.** Model choice within the TSFM class mattered more than TSFM-vs-classical.

### 5.2 Head-to-head negative results (the skeptical literature)

- **[Performance of Zero-Shot Time Series Foundation Models on Cloud Data](https://arxiv.org/abs/2502.12944)** (ICLR 2025 "I Can't Believe It's Not Better" workshop). Verbatim: *"FMs are outperformed consistently by simple linear baselines"* and *"FMs suddenly output seemingly erratic, random-looking forecasts."* Conclusion: *"Our results suggest a widespread failure of FMs to model cloud data."*
- **[How Foundational are Foundation Models for Time Series Forecasting?](https://arxiv.org/abs/2510.00742)** (NeurIPS 2025 workshop). *"Fine-tuned foundation models do not consistently yield substantially better results, relative to their increased parameter count and memory footprint, than smaller, dedicated models tailored to the specific forecasting task."* Also: *"the zero-shot capabilities of a time series foundation model are significantly influenced and tied to the specific domains it has been pretrained on"* — and no TSFM here was pretrained on consumer wearable data.
- **GIFT-Eval commentary:** on second-level frequency, only Chronos-2 and TimesFM-2.5 beat **AutoTheta**, a classical statistical method. Datasets at minutely/secondly granularity *"still favor strong statistical baselines — especially for short-term forecasting."*
- **[Against Time-Series Foundation Models](https://shakoist.substack.com/p/against-time-series-foundation-models):** when models with millions of parameters trained on millions of series beat a decent seasonal baseline by roughly a third on average, that indicates the amount of learnable structure in these problems is limited.
- **The TTM data point (§4.5):** a **0.8M-parameter** IBM model competes with 200M-parameter transformers. **The TabPFN-TS data point (§4.8):** an 11M model with **no time-series pretraining** ranks 1st on GIFT-Eval. Both undercut the scaling premise.

### 5.3 Anomaly detection: how it is done, and why the evidence is weak

**Three mechanisms in use:**
1. **Reconstruction error** — MOMENT in `reconstruction` mode. Anomaly score = per-timestep squared error between input and reconstruction. Verified in the [tutorial notebook](https://github.com/moment-timeseries-foundation-model/moment/blob/main/tutorials/anomaly_detection.ipynb).
2. **Forecast residual / predictive uncertainty** — forecast t+1 from history, score = |actual − predicted| normalised by the model's own prediction interval. Not built into Chronos; ~30 lines to add. Used by [Uncertainty-Driven Anomaly Detection for Psychotic Relapse Using Smartwatches](https://arxiv.org/abs/2605.13816), which derives a **daily anomaly score** from ensemble predictive uncertainty.
3. **Embeddings + trained detector head** — [ChronosAD](https://arxiv.org/html/2606.01300v1) uses Chronos zero-shot as a feature extractor, then trains a BiLSTM + multi-head-attention block. **Explicitly not zero-shot**; +4.72% AUC / +6.60% AP over 11 baselines.

**Why the evidence is weak — this is the most important methodological warning in this document.**

The AD benchmark literature is compromised by the **point-adjust** protocol, and MOMENT's headline zero-shot number sits squarely inside that problem. I confirmed by reading the notebook that the reported metric is:

```python
from momentfm.utils.anomaly_detection_metrics import adjbestf1
print(f"Zero-shot Adjusted Best F1 Score: {adjbestf1(y_true=labels, y_scores=anomaly_scores)}")
```

Two independent defects:
- **"adj" = point-adjusted.** [Kim et al., AAAI 2022](https://cdn.aaai.org/ojs/20680/20680-13-24693-1-2-20220628.pdf) showed *"a detection algorithm outputting random noise is expected to produce very good scores, and capable of outperforming state of the art methods on most of the common benchmark datasets."* Reproduced figure: **best-PA-F1 of i.i.d. random = 0.891**. [Wu & Keogh (2021)](https://arxiv.org/abs/2009.13807) separately showed **86.1% of Yahoo benchmark anomalies are found by a one-line moving-average algorithm**, and that most benchmark exemplars suffer known flaws such that *"much of the apparent progress in recent years may be illusionary."*
- **"best" = oracle threshold.** The threshold is swept against ground-truth labels. **A deployed early-warning system has no labels and therefore cannot reproduce this number.** Threshold selection is the hard part of anomaly detection, and this metric hands it to you for free.

**Consequence for this project:** if you report anomaly-detection F1, report **point-wise F1 at a threshold chosen without test labels** (e.g. from a held-out normal period), and report **a random-score and a moving-average control**. Doing this correctly is itself a defensible contribution, because most of the papers cited above do not.

### 5.4 Domain shift beats scale

Datadog built Toto and BOOM because general TSFMs underperformed on observability data ([arXiv 2505.14766](https://arxiv.org/abs/2505.14766)). [Generalist vs Specialist TSFMs on PPG](https://arxiv.org/abs/2510.14254) tested 51 tasks and found *"the specialist model achieves a 27% higher win score"* than generalist TSFMs like MOMENT. **Consistent message: for physiological signals, domain-matched pretraining beats general pretraining.** No available TSFM has wearable pretraining; the ones that do are bucket 5.

### 5.5 Benchmark leakage

[Rethinking Evaluation in the Era of Time Series Foundation Models](https://arxiv.org/abs/2510.13654) identifies train-test sample overlap and temporal overlap in TSFM evaluation: *"Ignoring these forms of information leakage when benchmarking TSFMs risks producing overly optimistic performance estimates that fail to generalize to real-world settings."* MOMENT's Time Series Pile includes the UCR archive and TSB-UAD — **the same sources many AD benchmarks draw from**, so MOMENT's zero-shot UCR AD results carry a live leakage risk. Treat every published zero-shot number as an upper bound.

### 5.6 Direct answers to the critical questions

**Q1 — Is there evidence TSFMs beat simple statistical baselines on short, gappy, low-dimensional, strongly seasonal wearable data?**
**One paper, one weak yes.** [arXiv 2607.20027](https://arxiv.org/abs/2607.20027): Chronos 0.82 vs EWMA 0.84 MASE at context 32 on 5-minute HRV from a consumer smartwatch, no fine-tuning. Statistically significant, practically ~2%. Against it: consistent negative results on cloud data, GIFT-Eval sub-hourly frequencies, and a general finding that zero-shot quality is bounded by pretraining-domain match. **Net: run the baseline, do not assume the TSFM wins.**

**Q2 — Has any TSFM been evaluated specifically on consumer wearable data?**
**Yes, three.** (i) [arXiv 2607.20027](https://arxiv.org/abs/2607.20027) — TimesFM/Chronos/MOIRAI zero-shot on Galaxy Watch HRV, the only true zero-shot consumer-wearable TSFM evaluation found. (ii) [AI on the Pulse](https://arxiv.org/abs/2508.03436) — UniTS, but **fine-tuned**, on 10-second HR/HRV. (iii) [arXiv 2605.13816](https://arxiv.org/abs/2605.13816) — smartwatch daily anomaly scores via predictive uncertainty. **None uses nightly-summary cadence.**

**Q3 — How is a forecasting/reconstruction model turned into an anomaly detector, and does it work?**
Three mechanisms, §5.3. It *works* in the sense that residual/reconstruction scores are non-trivial detectors. But the published evidence is undermined by point-adjusted best-F1, and no available TSFM offers deployable threshold selection. **The mechanism is sound; the reported effect sizes are not trustworthy.**

**Q4 — What context length is needed?** See §6.

**Q5 — Which run on a CPU-only laptop?** Chronos-Bolt (tiny/small/base), Chronos-2, MOMENT (small/base), TimesFM 2.5 via `[torch]`, TTM, TabPFN-TS, Lag-Llama. Degraded/blocked: Toto (Ampere recommended; 2.0 needs Python 3.12). Everything in bucket 5 is moot.

---

## 6. Context-length reality check against wearable cadences

Days of continuous data required to fill each model's context window.

| Model | Context | Nightly (1/day) | Hourly (24/day) | 5-minute (288/day) | 1-minute (1440/day) |
|---|---|---|---|---|---|
| Lag-Llama | 32 | **32 days** | 1.3 days | 1.7 hours | 21 min |
| HRV paper setting | 32–64 | 1–2 months | 1.3–2.7 days | 2.7–5.3 h | 21–43 min |
| Chronos-T5 (max) | 512 | **512 days = 1.40 years** | 21.3 days | 1.78 days | 8.5 hours |
| **MOMENT (FIXED)** | **512** | **512 days = 1.40 years** | 21.3 days | 1.78 days | 8.5 hours |
| **TTM (HARD MIN)** | **512** | **512 days = 1.40 years** | 21.3 days | 1.78 days | 8.5 hours |
| TTM-E branch | 1024 | 2.80 years | 42.7 days | 3.56 days | 17.1 hours |
| TTM-A branch | 1536 | 4.21 years | 64 days | 5.33 days | 25.6 hours |
| Chronos-Bolt (max) | 2048 | 5.61 years | 85.3 days | 7.1 days | 34.1 hours |
| Chronos-2 (max) | 8192 | 22.4 years | 341 days | 28.4 days | 5.7 days |
| TimesFM 2.5 (max) | 16384 | 44.9 years | 683 days | 56.9 days | 11.4 days |

### How to read this — the distinction the prior research missed

**"Maximum context" and "required context" are completely different things, and the difference decides this project.**

- **Chronos-T5 / Chronos-Bolt / Chronos-2 / TimesFM / Lag-Llama / TabPFN-TS: context is a MAXIMUM.** They accept any length and NaN-pad. The HRV paper ran Chronos-bolt-base at **context 32** and got the best result in the study. **At nightly cadence, ~30–60 nights is enough to start.**
- **MOMENT: 512 is FIXED.** Shorter input is legal but **left-padded with zeros**. At nightly cadence with 90 nights of data, **422 of 512 input positions (82%) are padding.** The `input_mask` argument tells the model to ignore them, but you are running a 346M-parameter model on 18% real signal, and the model was pretrained on dense 512-length windows. Expect degradation and do not assume the published UCR numbers transfer.
- **TTM: 512 is a HARD MINIMUM.** *"the model needs a minimum context length of 512 or 1024."* **At nightly cadence TTM is simply unusable without 1.4 years of history.** Despite being the most CPU-friendly model in the survey, TTM is disqualified for nightly data.

**Bottom line by cadence:**
- **Nightly summary:** only the Chronos family, TimesFM, Lag-Llama and TabPFN-TS are viable. MOMENT is degraded; **TTM is out**.
- **Hourly:** ~3 weeks of data unlocks MOMENT and TTM; everything becomes viable.
- **5-minute:** ~2 days unlocks essentially everything. This is the cadence at which the published wearable evidence (§5.1) was actually collected.

---

## 7. Repository health table

All figures pulled from the GitHub and HuggingFace REST APIs on **2026-08-30**.

| Repo | Stars | Open issues | Last push | Licence | Verdict |
|---|---|---|---|---|---|
| google-research/timesfm | 28,314 | 224 | 2026-08-28 | Apache-2.0 | Very active; high issue count tracks popularity |
| amazon-science/chronos-forecasting | **5,776** | **36** | **2026-08-14** | Apache-2.0 | **Healthiest overall — best stars:issues ratio** |
| SalesforceAIResearch/uni2ts | 1,580 | 49 | 2026-06-02 | Apache-2.0 | Active, but NC licence and old pins |
| time-series-foundation-models/lag-llama | 1,601 | 66 | 2025-06-06 | Apache-2.0 | **Stale**; worst issue ratio |
| ibm-granite/granite-tsfm | 884 | **5** | 2026-08-28 | Apache-2.0 | **Cleanest tracker**; very active |
| moment-timeseries-foundation-model/moment | 833 | 21 | 2026-02-10 | **MIT** | Maintained but slowing; hard dep pins |
| mims-harvard/UniTS | 647 | 28 | **2024-09-26** | MIT | **~23 months stale** |
| DataDog/toto | 538 | 25 | 2026-08-25 | Apache-2.0 | Healthy, active |
| Nokia-Bell-Labs/papagei-foundation-model | 176 | 5 | 2025-07-08 | BSD-3-Clause | Quiet but tidy |
| Mobile-Sensing…/NormWear | **63** | 5 | 2026-04-27 | Apache-2.0 | **Low adoption**; you'd be an early user |
| davegabe/ai-on-the-pulse | **12** | — | 4 commits total | — | **Not a reusable artifact** |

**HF download counts as an adoption proxy:** `amazon/chronos-2` 29,603,437 · `autogluon/chronos-2` 5,508,107 · `amazon/chronos-bolt-small` 6,933,938 · `ibm-granite/granite-timeseries-ttm-r2` 390,810 · `Datadog/Toto-Open-Base-1.0` 197,069 · `AutonLab/MOMENT-1-small` 64,218 · `Salesforce/moirai-moe-1.0-R-base` 59,258 · `google/timesfm-2.0-500m-pytorch` 30,727 · **`mosaic-laboratory/normwear` 22** · **`mosaic-laboratory/normwear2` 100**. The wearable-specific models have essentially no user base.

**Install-friction ranking (from PyPI `requires_dist`, lower is better):**
1. `momentfm` — 4 deps, but **exact pins**: `numpy==1.25.2`, `transformers==4.33.3`, `huggingface-hub==0.24.0`. Isolated venv mandatory.
2. `timesfm[torch]` — clean: numpy, hf-hub, safetensors, torch. **Do not use `[flax]`/`[xreg]` (jax[cuda])**.
3. `chronos-forecasting` — 23 deps but **all range-pinned** (`torch<3,>=2.2`, `transformers<6,>=4.41`). **Most forgiving resolver behaviour.**
4. `granite-tsfm` — 35 deps, python >=3.11,<3.14, torch>=2.10.
5. `uni2ts` — 29 deps, old pins (`torch<2.5`, `datasets~=2.17.1`), hydra configs.
6. `toto-ts` — 32 deps, `torch==2.7.0` exact. `toto-models` needs **Python >=3.12**.

---

## 8. What is genuinely usable in a 2-week project with ~45 build hours

### Tier A — use these (≈8–12h total)

| Item | Hours | Why |
|---|---|---|
| **Chronos-Bolt-tiny/small** as a forecaster | 2–4 | Only model that is simultaneously bucket 2, Apache-2.0, CPU-documented, short-context tolerant, and NaN-native. 8.65M params. |
| **Chronos-2** if multivariate matters | +1–2 | Same install; adds joint cross-channel modelling and covariates zero-shot. |
| **Forecast-residual anomaly scorer** on top | 2–3 | ~30 lines: score = abs(actual − median forecast) / interval width. |
| **Classical baselines (rolling median + MAD, EWMA, seasonal-naive, CUSUM)** | 2–3 | **Non-negotiable.** §5.1 says they may win. This comparison is the project's most defensible contribution. |

### Tier B — only if Tier A finishes early (≈5–8h)

- **MOMENT-1-small** for reconstruction-based AD, **in a separate venv**. Genuinely zero-shot, genuinely mask-aware. But: fixed-512 padding problem at nightly cadence, dependency pins, and the "cannot detect vertical shifts" limitation that hits our use case directly.
- **TimesFM 2.5** as a second forecaster (`timesfm[torch]`, Apache-2.0). Cheap once Chronos plumbing exists.

### Tier C — do not attempt

| Item | Reason |
|---|---|
| **NormWear / NormWear2** | Wrong input type (raw 64 Hz waveforms vs our summaries); embeddings need a trained head; no pip package; 22 HF downloads; 12–20h. |
| **PaPaGei / Pulse-PPG** | Require raw PPG waveforms that consumer wearable APIs do not export. Bucket 3. |
| **UniTS** | Last push 2024-09-26; bash + YAML + full dataset download; 15–25h. Its headline result was fine-tuned anyway. |
| **Toto 2.0** | Requires Python >=3.12; local env 3.11.9. Toto 1.0 wants an Ampere GPU. |
| **TTM** | **Hard 512-sample minimum** = 1.4 years of nightly data. Disqualified by cadence despite being the most CPU-friendly model here. |
| **Moirai** | CC-BY-NC-4.0; heavy old pins; **was the worst TSFM in the one wearable study**. |
| **TimeGPT** | Sending participant physiological data to a third-party commercial API. Pricing unverifiable (404s). |
| **Apple WBM / LSM-2 / SensorFM / HeartBEiT** | **Weights do not exist publicly.** Zero hours available at any budget. |
| **Training/fine-tuning anything** | Out of scope at 45h, and would forfeit the zero-shot framing. |

### The honest framing for the writeup

The most intellectually defensible result available in 45 hours is **not** "we deployed a foundation model." It is:

> We evaluated whether a pretrained time-series foundation model provides measurable benefit over classical statistical baselines on short, gappy, strongly circadian consumer wearable data, and we measured anomaly detection with a threshold selected without access to test labels — unlike most of the literature we compare against.

That is a real finding either way, it engages directly with a live methodological controversy (§5.3), and it is achievable. It also lets you cite Apple's WBM result (§4.15) as principled justification for working at the derived-metric level rather than treating that as a limitation.

---

## 9. Bibliography

**General TSFMs — primary sources**
- Chronos repo: https://github.com/amazon-science/chronos-forecasting
- Chronos-2 model card: https://huggingface.co/amazon/chronos-2 · config: https://huggingface.co/amazon/chronos-2/raw/main/config.json
- Chronos-2 technical report: https://arxiv.org/abs/2510.15821
- Chronos paper: https://arxiv.org/abs/2403.07815
- Chronos-Bolt / AutoGluon blog: https://aws.amazon.com/blogs/machine-learning/fast-and-accurate-zero-shot-forecasting-with-chronos-bolt-and-autogluon/
- chronos-forecasting on PyPI: https://pypi.org/project/chronos-forecasting/
- MOMENT paper (ICML'24): https://arxiv.org/abs/2402.03885
- MOMENT repo: https://github.com/moment-timeseries-foundation-model/moment
- MOMENT AD tutorial (the zero-shot evidence): https://github.com/moment-timeseries-foundation-model/moment/blob/main/tutorials/anomaly_detection.ipynb
- MOMENT-1-large card + config: https://huggingface.co/AutonLab/MOMENT-1-large · https://huggingface.co/AutonLab/MOMENT-1-large/raw/main/config.json
- momentfm on PyPI: https://pypi.org/project/momentfm/
- TimesFM repo: https://github.com/google-research/timesfm · PyPI: https://pypi.org/project/timesfm/
- TimesFM 3.0 (non-commercial licence): https://huggingface.co/google/timesfm-3.0-pytorch
- TimesFM 2.5 (Apache-2.0): https://huggingface.co/google/timesfm-2.5-200m-pytorch
- Moirai / uni2ts: https://github.com/SalesforceAIResearch/uni2ts · https://huggingface.co/Salesforce/moirai-1.1-R-large
- Lag-Llama: https://github.com/time-series-foundation-models/lag-llama · https://huggingface.co/time-series-foundation-models/Lag-Llama
- TTM / granite-tsfm: https://github.com/ibm-granite/granite-tsfm · https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2 · https://pypi.org/project/granite-tsfm/
- UniTS: https://github.com/mims-harvard/UniTS · weights: https://github.com/mims-harvard/UniTS/releases/tag/ckpt
- Toto: https://github.com/DataDog/toto · https://huggingface.co/Datadog/Toto-Open-Base-1.0 · https://huggingface.co/Datadog/Toto-2.0-313m
- Toto/BOOM paper: https://arxiv.org/abs/2505.14766
- TabPFN-TS: https://github.com/PriorLabs/tabpfn-time-series · https://arxiv.org/abs/2501.02945 · https://pypi.org/project/tabpfn-time-series/
- Nixtla/TimeGPT client: https://pypi.org/project/nixtla/ (pricing pages returned 404 on 2026-08-30 — cost UNVERIFIED)

**Physiological / wearable foundation models**
- NormWear: https://github.com/Mobile-Sensing-and-UbiComp-Laboratory/NormWear · https://huggingface.co/mosaic-laboratory/normwear
- NormWear2: https://huggingface.co/mosaic-laboratory/normwear2 · paper: https://arxiv.org/abs/2605.15465
- PaPaGei (ICLR'25): https://github.com/Nokia-Bell-Labs/papagei-foundation-model (weights: Zenodo record 13983110)
- Pulse-PPG (UbiComp'25): https://arxiv.org/abs/2502.01108 · https://github.com/maxxu05/pulseppg (weights: Zenodo 10.5281/zenodo.17270930)
- PPG FM independent benchmark: https://github.com/Misterbra/ppg-age-benchmark
- Apple WBM: https://arxiv.org/abs/2507.00191
- Apple biosignal FM (earlier): https://arxiv.org/abs/2312.05409
- Apple RelCon motion FM: https://arxiv.org/abs/2411.18822
- Google LSM-2: https://arxiv.org/abs/2506.05321 · https://research.google/blog/lsm-2-learning-from-incomplete-wearable-sensor-data/
- Google SensorFM: https://research.google/blog/sensorfm-towards-a-general-intelligence-and-interface-for-wearable-health-data/
- HeartBEiT: https://arxiv.org/abs/2212.14040 (**weights withheld**)
- ECG-FM: https://huggingface.co/wanglab/ecg-fm · https://github.com/bowang-lab/ECG-FM
- ECGFounder: https://github.com/PKUDigitalHealth/ECGFounder
- SleepFM community ports: https://huggingface.co/braindecode/SleepFM

**Evaluations, benchmarks, and skeptical work**
- **Zero-Shot HRV Forecasting from Consumer Wearables** (most on-point): https://arxiv.org/abs/2607.20027
- AI on the Pulse (CIKM'25): https://arxiv.org/abs/2508.03436 · code: https://github.com/davegabe/ai-on-the-pulse · ACM: https://dl.acm.org/doi/10.1145/3746252.3760799
- Zero-Shot TSFMs on Cloud Data (**FMs lose to linear baselines**): https://arxiv.org/abs/2502.12944
- How Foundational are Foundation Models for TS Forecasting?: https://arxiv.org/abs/2510.00742
- (Un)known Information Leakage in TSFM evaluation: https://arxiv.org/abs/2510.13654
- Generalist vs Specialist TSFMs on PPG (**specialists +27% win score**): https://arxiv.org/abs/2510.14254
- ChronosAD: https://arxiv.org/html/2606.01300v1
- Uncertainty-Driven AD for Psychotic Relapse (smartwatches, daily scores): https://arxiv.org/abs/2605.13816
- **Kim et al., Towards a Rigorous Evaluation of TSAD** (random noise scores ~0.89 PA-F1): https://cdn.aaai.org/ojs/20680/20680-13-24693-1-2-20220628.pdf
- **Wu & Keogh, Current TSAD Benchmarks are Flawed**: https://arxiv.org/abs/2009.13807
- Post-point-adjustment metric stress test: https://arxiv.org/html/2607.11969v1
- Against Time-Series Foundation Models: https://shakoist.substack.com/p/against-time-series-foundation-models
- TSFM strengths and limitations: https://aihorizonforecast.substack.com/p/time-series-foundation-models-a-deep

---

## Appendix — verified numbers reference

Pulled from HF/GitHub/PyPI APIs on 2026-08-30. Params are `safetensors.total` (actual tensor element counts), not paper-reported figures.

| Model id | Params | Licence | Downloads | Last modified |
|---|---|---|---|---|
| amazon/chronos-2 | 119,477,664 | apache-2.0 | 29,603,437 | 2026-06-05 |
| autogluon/chronos-2 | 119,477,664 | apache-2.0 | 5,508,107 | 2026-06-05 |
| amazon/chronos-bolt-tiny | 8,652,672 | apache-2.0 | 1,070,180 | 2025-11-21 |
| amazon/chronos-bolt-mini | 21,236,096 | apache-2.0 | 157,278 | 2025-11-21 |
| amazon/chronos-bolt-small | 47,718,016 | apache-2.0 | 6,933,938 | 2025-11-21 |
| amazon/chronos-bolt-base | 205,292,928 | apache-2.0 | 1,243,025 | 2025-11-21 |
| amazon/chronos-t5-small | 46,154,240 | apache-2.0 | 915,614 | 2025-11-21 |
| AutonLab/MOMENT-1-small | 37,901,512 | **mit** | 64,218 | 2025-03-26 |
| AutonLab/MOMENT-1-base | 113,481,608 | **mit** | 38,751 | 2025-03-26 |
| AutonLab/MOMENT-1-large | 346,368,520 | **mit** | 36,505 | 2025-03-26 |
| google/timesfm-2.0-500m-pytorch | 498,828,960 | apache-2.0 | 30,727 | 2025-04-16 |
| google/timesfm-2.5-200m-pytorch | 231,289,280 | apache-2.0 | — | 2025-10-02 |
| google/timesfm-3.0-pytorch | 330,710,976 | **non-commercial** | — | 2026-08-28 |
| Salesforce/moirai-1.0-R-small | 13,827,528 | **cc-by-nc-4.0** | 80,196 | 2025-01-21 |
| Salesforce/moirai-1.1-R-large | 310,970,624 | **cc-by-nc-4.0** | 34,529 | 2025-01-21 |
| Salesforce/moirai-moe-1.0-R-small | 117,099,528 | **cc-by-nc-4.0** | 8,346 | 2025-01-21 |
| Salesforce/moirai-moe-1.0-R-base | 935,361,504 | **cc-by-nc-4.0** | 59,258 | 2025-01-21 |
| ibm-granite/granite-timeseries-ttm-r2 | 805,280 | apache-2.0 | 390,810 | 2025-02-26 |
| ibm-granite/granite-timeseries-ttm-r1 | 805,280 | apache-2.0 | 27,073 | 2025-01-30 |
| Datadog/Toto-Open-Base-1.0 | 151,306,080 | apache-2.0 | 197,069 | 2026-05-14 |
| Datadog/Toto-2.0-4m | 4,144,448 | apache-2.0 | 103,151 | 2026-06-04 |
| Datadog/Toto-2.0-22m | 21,915,584 | apache-2.0 | 88,679 | 2026-06-04 |
| Datadog/Toto-2.0-313m | 312,684,608 | apache-2.0 | 31,256 | 2026-06-04 |
| time-series-foundation-models/Lag-Llama | 2,449,299 | apache-2.0 | — | 2024-05-14 |
| **mosaic-laboratory/normwear** | **193,812,170** | apache-2.0 | **22** | 2026-04-27 |
| mosaic-laboratory/normwear2 | (not exposed) | apache-2.0 | 100 | 2026-08-29 |

**Verified context lengths (read from `config.json`):**
`amazon/chronos-t5-small` → `context_length: 512`, `prediction_length: 64` ·
`amazon/chronos-bolt-base` → `context_length: 2048`, `input_patch_size: 16`, `prediction_length: 64` ·
`amazon/chronos-2` → `context_length: 8192`, `input_patch_size: 16` ·
`AutonLab/MOMENT-1-large` → `seq_len: 512`, `patch_len: 8`, `patch_stride_len: 8`, `device: "cpu"`, backbone `google/flan-t5-large`
