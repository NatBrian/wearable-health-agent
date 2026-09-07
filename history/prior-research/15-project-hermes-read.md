# 15. Project Hermes: the blocking read, done

`research/01-problem-formulation.md` and `research/10-evidence-synthesis.md` both flagged one preprint
as a **blocking read before anything is designed**. The design was written before it was read. This
document closes that gap and records what it costs us.

## The paper

**Project Hermes: A Model-Agnostic Validation Layer for Wearable Health Prediction Systems**
Richik Chakraborty. arXiv:2602.18643. Submitted 20 February 2026.

Verified at source: `https://arxiv.org/abs/2602.18643` resolves to a real record with that title,
author and date. An earlier check using the arXiv API returned nothing, but the same call returned
nothing for a known-good control identifier, so that result was an artefact of the query, not
evidence about the paper. Recorded here because a false "this citation is fabricated" conclusion
would have been worse than not checking at all.

### What it does

A validation layer that sits **downstream of any prediction model**, hence "model-agnostic". When the
upstream predictor raises an alert, Hermes issues **LLM-generated contextual queries** to the user and
applies **Bayesian updating** to the alert's confidence, separating genuine signals from false alarms.

Reported on a migraine prediction task:

| Metric | Value |
|---|---|
| False positive rate | **61.7% to 12.5%** |
| Sensitivity maintained | **89%** |
| Mean lead time | 4.2 hours before symptom onset |

The paper is explicit that it performs **validation, not diagnosis**, and frames validation as "a
first-class computational problem distinct from prediction".

### Evidential weight

Single author, single preprint, no released code, one condition, no independent replication. Treat
the numbers as indicative, not established. It is nonetheless **real prior art for the core
mechanism** and must be cited.

## What this invalidates

One sentence appeared in both `PROPOSAL.md` and `README.md`:

> Nothing connects a detected physiological deviation to a targeted question capable of resolving it.

**That is now false.** Hermes connects exactly that. The claim has been corrected in both files. This
is the specific reason the read was marked blocking, and the cost of deferring it was shipping a
proposal with a false novelty claim in its opening summary.

## What survives, and why

The overlap is real but partial. Hermes takes *asking a question and Bayesian-updating on the answer*.
It does not take the following.

**1. Deciding whether to ask at all.** Hermes asks because an alert fired. Our agent computes the
expected information gain of each candidate question against a quantified interruption cost, in the
form given by Horvitz, Jacobs and Hovel (UAI 1999), and against an explicit interruption budget. It
can choose `OBSERVE` and stay silent on a night when a question would not pay for itself. Hermes has
no equivalent of choosing silence, because validating an alert is its only job. This is the
difference between a validator and a policy.

**2. An action space wider than asking.** Ours is `OBSERVE / ASK / MEASURE / ESCALATE / CONCLUDE`.
`MEASURE` orders a specific reading on the watch, so the agent can acquire evidence without spending
user attention at all. Hermes asks or does not.

**3. A grounded differential.** Hermes explicitly does not diagnose. We produce a ranked differential
with retrieval-backed citations and claim-to-source enforcement, and a typed terminal disposition
including `INSUFFICIENT_DATA`.

**4. Multi-night reasoning.** Our episode holds state across nights and waits, with persistence and
debouncing. Hermes operates per alert.

**5. Domain.** Migraine prediction against infection and illness triage. Different physiology,
different confounders, different red flags.

## How the framing changes

The honest positioning is now **stronger**, not weaker.

Before, the claim was "nobody does this", which was one preprint away from being wrong, and now is
wrong. After, the claim is: **the mechanism has a published precedent that reports it works, and this
project extends it from validation into decision.** That is a better claim for a portfolio piece,
because it is defensible and it demonstrates awareness of the literature rather than ignorance of it.

Hermes also hands us something useful: **a number to position against.** 61.7% to 12.5% at 89%
sensitivity is a concrete comparator for our own evaluation, on a different condition and with a
different mechanism, and citing it is more credible than reporting our result in a vacuum.

## Actions taken

- Novelty claim corrected in `PROPOSAL.md` section 1 and section 2.4.
- Gap statement corrected in `README.md`.
- Hermes added to the "what already exists" table in `PROPOSAL.md` 2.4.
- Hermes added to `PROPOSAL.md` Appendix C.

## Actions still open

- The evaluation plan (`PROPOSAL.md` 4.7) should state the Hermes figures as an external comparator
  and be explicit that our task is not the same task, so the numbers are context and not a target.
- If Hermes releases code, re-check whether the information-gain gating is genuinely absent or merely
  undescribed in the abstract.
