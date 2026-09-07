# Handover: the agentic flow

> **COMPLETE, 4 September 2026.** All five items in the plan below were done, and the work
> carried on well past them: the red-flag design was replaced with a validated decision
> rule, the conversation became genuinely multi-turn on both the dashboard and Telegram,
> the dashboard became an HTTP client so it can be swapped for React, and the consumer
> health corpus layer was fetched. **Read `STATUS.md` for where things actually stand.**
> This file is kept for the reasoning it records, not as a list of things to do.

**Written 3 September 2026, mid-task.** The production simulation is finished and its
defects are fixed. This document covers the piece that is planned but **not started**:
whether the agent reasons like an agent, and whether what it says is grounded and cited.

Read `STATUS.md` first, then this.

---

## Where the machine is right now

- **Nothing is running.** No dashboard, no mock watch, no scheduler.
- **`.env` is pointed at the simulation**, not the phone: `WHA_SUBJECT=sim`,
  `WHA_BRIDGE_URL=http://127.0.0.1:8788`. The original is `.env.phase4-backup`.
  **Restore it before using the real watch again.**
- **Two subjects.** `me` holds the four real nights (44, 45, 45, 47 bpm) and is archived at
  `archive/dbs/wha-real-4nights-20260903-1630.sqlite`. `sim` holds about six weeks of
  simulated nights from the scenario run and can be deleted freely.
- Schema is **v5**. 450 tests pass, 1 skipped.

To resume the simulation: start `tools/mock_watch.py serve`, then `uv run wha serve`, then
`tools/mock_watch.py day --scenario <name>`. See `docs/RUNBOOK-SIMULATION.md`.

---

## What the simulation established

Seven scenarios were run as an ordinary person: healthy nights, nights with exercise, an
office party, feeling rough afterwards, a light fever, a sore throat, severe diarrhoea.

**Working.** Twenty healthy nights produced no interruptions. A workout that raised resting
heart rate by 4 bpm, enough to be RED, was correctly attributed and did not interrupt. Told
"nothing unusual" the system concluded benign; told "feverish" on the same shape of signal
it concluded likely illness. The tool allow-list refused seven calls to tools that do not
exist, and audited every refusal.

**Fixed during the run.** Thirteen defects, then two more the user found by reading their
own phone. They are described in the commits from `Close eleven gaps a simulated user
walked into` onward. Nearly all were the same shape: something defined, referenced by other
code, and never reached.

---

## The open work: five items

### The finding that matters

The graph does cycle. `investigate` has a real tool loop, `ask` routes back to `believe`,
and question selection is EVSI-driven, which is the principled form of "which query is
worth making". This is not a chatbot.

But the cycle never returns to `investigate`:

```
START → preload → investigate → believe → decide → ask → believe → decide → …
                       ^
                  runs ONCE, before the person has said anything
```

The agent gathers evidence **once, before it has asked a single question**, and can never
gather more in light of the answer. Consequences observed in the run:

- `retrieve_clinical_evidence` was called **zero times in 145 tool calls**. The only moment
  it could fire is before any symptom is known, so there is nothing to look up.
- After an answer the agent can only re-run arithmetic over the same facts, so the belief
  barely moves and it concludes at once.
- Every episode asked exactly **one** question and never followed up, even holding stress at
  0.87 against infection at 0.46.

### Supporting research

- Bani-Harouni, Pellegrini, Özsoy, Navab and Keicher 2025, *Language Agents for
  Hypothesis-driven Clinical Decision Making with Reinforcement Learning*, arXiv:2506.13474.
  The agent "generates hypotheses and selectively queries data based on diagnostic value"
  and refines through "a feedback loop where each observation either strengthens or weakens
  particular hypotheses", stopping "once the model reaches adequate certainty".
- MeDxAgent, arXiv:2606.03416, and the npj Artificial Intelligence scoping review
  (s44387-025-00011-z): feeding candidate diagnoses back into targeted questioning improves
  accuracy. That is precisely the missing edge.

The hard parts already exist here: a real Bayesian hypothesis state, EVSI for choosing the
next query, and veto gates as a stopping criterion. What is missing is the cycle.

### The plan

| # | Item | Detail |
|---|---|---|
| 1 | **Route `ask → investigate → believe`** | The one edge that makes it iterative. `route_after_ask` in `agent/graph.py` currently returns `believe` or `conclude`. Watch `tool_call_count` against its ceiling when re-entering. |
| 2 | **Build `data/knowledge/corpus.yaml`** | From sources a human already chose: `causes.yaml` carries a citation per field, `red_flags.yaml` a rationale per rule, `constants.py` holds Alavi 2022, Bloomfield 2024, Whitehurst 2018, Dial 2025, Mishica 2022. **Invent no medical content.** |
| 3 | **Populate `retrieval_index`** | `EpisodeRepository.__init__` sets it to `None` and nothing ever assigns it, so `tool_retrieve_clinical_evidence` can never return a passage. `retrieve/index.py` has the HybridIndex. |
| 4 | **Populate `citations` and `evidence_used`** | `agent/nodes.py:776` hardcodes `citations=[]` and `unsupported_claims=0`. That silently disables the claim-to-source enforcement `docs/CONTRACTS.md` line 1218 specifies, and makes the grounding check in `retrieve/grounding.py` unreachable. |
| 5 | **Ground the differential** | Every entry carries a probability with `supporting: []` and `contradicting: []`, so a number appears with no reason attached. Fill from the facts already gathered. |

### The decision left open

Item 1 will make the agent ask **more** questions, because after an answer it will often
still be uncertain. The weekly interruption budget is what stops that becoming nagging.
Follow-ups *within* one episode may feel quite different from repeated interruptions across
days, and the user should judge that once it is visible rather than have it settled in
advance. The user was asked whether to do items 2 to 5 first and hold item 1, or do all
five and judge in the retest; **the answer was not given before the session ended.** Ask
again.

---

## Things deliberately left alone

- `text_source` records `"fallback"` even when the model wrote the text. The behaviour is
  correct, the label is wrong. Small.
- `get_nightly_features` was called 101 times in one run. Probably wasteful, not
  investigated.
- Whether a synthetic subject should be able to notify a real phone at all. Recorded in
  `BLOCKERS.md`.
- The frozen scenario `no-response-timeout` still fails one expectation: a timed-out
  question closes `LIKELY_BENIGN` where `UNRESOLVED` is honest. Recorded in `BLOCKERS.md`.
