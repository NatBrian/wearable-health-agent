# Experiments

> ## Read this before you read anything else in this folder
>
> **Nothing here is a clinical trial.**
> **Nothing here is peer reviewed.**
> **Nothing here was validated against a clinical outcome, on any patient, ever.**
>
> **None of it supports a claim that this system detects illness in real use.**
>
> These are engineering experiments run by the author, on the author's own code, scored by
> the author. They exist to explain why the system is built the way it is. They are not
> evidence that it works, and they must not be quoted anywhere in this repository as
> though they were.

---

## Why this folder exists at all

Until 7 September 2026 these numbers were spread through the README, the architecture
document, the dashboard and the demo film, presented as measurements. A film card opened
with "The sensor alone cannot separate them. This was measured." The 40 cases behind that
sentence are synthetic, and the ground truth is a label this project injected itself.

That is not a measurement of anything about health. Quarantining these results here, behind
a disclaimer, is the only honest place for them.

## What is in here, and what each thing is worth

| Folder | What it is | What it is worth |
|---|---|---|
| `detection/` | Our re-analysis of the public wearable dataset released with Mishra et al. 2020 | Real people's data, our analysis. Not peer reviewed. One cohort, one device, one illness, and the participants were Fitbit users in a COVID-19 study rather than any general population |
| `policy-simulation/` | 40 synthetic cases comparing question-asking strategies | **Self-scored.** The ground truth is a label we injected, and a simulated person answers every question truthfully and immediately. It measures whether our code recovers a label we planted. It says nothing about a person |
| `retrieval/` | Sixteen configurations of a search reranker | An engineering comparison of our own retrieval against itself |
| `forecasting/` | The neural forecaster that was built, compared against plain arithmetic, and deleted | An engineering decision, recorded so it is not repeated |

## The distinction that matters

Two kinds of number look identical on a page and are not the same thing.

**A published finding**, from a study designed to answer a clinical question, reviewed by
people who were not the authors, on a population the finding is claimed for. The Marburg
Heart Score in this project is one: derived on 1,199 patients, validated externally, and
used here for the presentation it was validated on.

**A number we produced ourselves**, on our own code, scored by our own labels. Everything in
this folder.

The second kind can tell you why a design choice was made. It cannot tell you the design
choice was right, and it cannot tell anybody that this system is safe or effective.

## If you are looking for what this system actually claims

`DISCLAIMER.md` at the repository root, and the disclosures on the dashboard. The short
version is that how well this detects illness in real use **has not been established**, and
this project is not a medical device.
