# Component 09. The agent graph

**Phase:** B. **Module:** `src/wha/agent/`. **Depends on:** 07 belief, 08 policy, 10 tools,
11 safety, 13 LLM client.

LangGraph with a SQLite checkpointer. Holds one episode's state across days, survives the endpoint
being down, and terminates.

---

## 1. The graph

```
                     ENTRY
                       |
                 [ preload ]            deterministic. Loads the cheap T1 reads
                       |
                 [ investigate ] <---+  THE LLM DRIVES. Free tool calls
                       |             |
                  tool needed? ------+
                       | no
                 [ believe ]           deterministic. Component 07
                       |
                 [ decide ]            deterministic. Component 08
                       |
        +--------------+-------------------+-----------+
        |              |                   |           |
   [ observe ]    [ ask ]            [ measure ]  [ conclude ]
        |              |                   |           |
       END      interrupt()          interrupt()  [ critique ]
                       |                   |           |
                  (resumes)           (resumes)   [ review ] --> END
                       |                   |
                       +-------------------+
                                 |
                          back to [ believe ]
```

`escalate` is **not a node**. The red-flag intercept runs in component 11 *before* the graph is
entered, and an escalation from the belief is emitted by `decide` as a terminal action. Nothing
inside the graph can reach an escalation the safety layer did not already permit.

---

## 2. State

```python
class EpisodeState(TypedDict):
    episode_id: str
    subject_id: str
    nights: Annotated[list[Detection], add_nights]      # reducer, dedupes by night_date
    features: list[NightlyFeatures]
    preloaded: dict[str, Any]                            # the cheap T1 reads
    tool_calls: Annotated[list[ToolCall], operator.add]
    evidence: Annotated[list[ExtractedFact], operator.add]
    answers: Annotated[list[Answer], operator.add]
    measurements: Annotated[list[MeasurementResult], operator.add]
    belief: BeliefState | None
    action: Action | None
    draft: EpisodeOutcome | None
    step: int
    tool_call_count: int
    depth_used: int
```

**Design the state so the audit log falls out of the checkpointer**, rather than maintaining a
parallel log that can drift. `created_at`, `values`, `next` and `interrupts` per snapshot are already
most of the required fields; `sources` and `human_decision` are put into the state deliberately so
they land in the checkpoint too.

`thread_id` is the `episode_id`. One thread, one episode, for its whole life.

---

## 3. The nodes

### `preload` (deterministic)

Fetches nightly features, personal baseline, known events, data quality and the episode's own
history, and puts them in `state["preloaded"]`.

**This is an optimisation, not a restriction.** Every T1 tool remains callable from `investigate`,
including re-fetching a preloaded one with different arguments. It exists because making the model
spend turns at roughly nine tokens per second fetching what it always needs buys nothing and adds
ordering nondeterminism to the cassette tests.

### `investigate` (the LLM drives)

The agentic loop. The model is given the preloaded context and the T1 tool table, and it decides
what else to read, in what order, and when it has enough.

Its judgement is concentrated where it matters: **constructing the retrieval query from this case,
re-querying after learning something, choosing the pattern for `find_similar_past_episodes`, and
deciding to stop.**

- Terminates when the model emits no tool call, or at `MAX_TOOL_CALLS_PER_EPISODE`.
- Output is a **typed** `list[ExtractedFact]`. Untrusted text has nowhere to go: it is not in the
  output schema.
- `LLMUnavailable` here **parks the episode**. State is checkpointed, the node returns without
  advancing, and `episode_tick` retries on the next interval. It never fabricates and never closes.

### `believe` (deterministic)

Component 07, recomputed from scratch over the whole episode. Writes a `beliefs` row with its
trigger.

### `decide` (deterministic)

Component 08. Returns exactly one `Action` with its `rationale` and the full `rejected` list.

**One LLM call is permitted here, and only in one direction:** the veto. Having read the case, the
model may cancel an authorised `ASK` as redundant. It cannot authorise one that was declined, and the
interface makes that impossible rather than merely discouraged. A veto is recorded, does not consume
budget, and is reported as a count.

### `ask` and `measure`

Both: draft, validate, send, then `interrupt()`.

```python
# EVERYTHING before interrupt() must be idempotent, because resuming
# re-runs the node from the top. This is the single most common LangGraph error.
interaction_id = upsert_interaction(...)   # keyed, idempotent
notify_if_not_already_sent(interaction_id) # checks notifications table first
answer = interrupt({"kind": "question", "interaction_id": interaction_id})
```

The comment is in the source, not only here.

### `conclude`, `critique`, `review`

`conclude` drafts the `EpisodeOutcome`. `critique` runs **deterministic** claim-to-source
enforcement first, then the LLM coherence pass which may only strip more. `review` is the human
checkpoint: `interrupt()` with the draft, resumed by approve, edit, reject or escalate.

---

## 4. Interrupts, and the rule that bites

**Resuming an `interrupt()` re-runs the whole node from the start.** Not from the interrupt.

Therefore, in every node containing one:

- No non-idempotent operation before the `interrupt()` call. Sends are guarded by a check against
  `notifications`; writes are upserts keyed on a deterministic id.
- Never wrap `interrupt()` in a bare `try/except`.
- Never conditionally skip or reorder `interrupt()` calls within a node.
- Only JSON-serialisable values pass through.

**LangGraph has no built-in timeout on a human wait.** Timeouts are external: `episode_tick`
(component 17) checks `ANSWER_TIMEOUT_HOURS` and `MEASUREMENT_TIMEOUT_HOURS` and resumes the graph
with a `TIMED_OUT` answer. **Non-response is a designed path**, not a failure, and the policy must
reach a sensible disposition without an answer, because much of the time it will not get one.

---

## 5. Stop conditions

Three, composed, checked in order:

1. **A disposition is reached.** The real one.
2. **A cap is hit.** `EPISODE_MAX_STEPS`, `MAX_TOOL_CALLS_PER_EPISODE` or `EPISODE_MAX_NIGHTS`.
   Closes `UNRESOLVED` with a `safety_event`. A net, not an expected path.
3. **A wait deadline expires** with nothing left worth doing. Closes `UNRESOLVED` or
   `INSUFFICIENT_DATA`.

`recursion_limit` is set to `EPISODE_MAX_STEPS`, and `GraphRecursionError` is caught and converted
into an `UNRESOLVED` close rather than propagating. An uncaught recursion error would lose the
episode.

---

## 6. Resumption and the endpoint being down

The endpoint is expected to be unavailable most of the time. That is the design point, not a
degraded mode.

| Situation | Behaviour |
|---|---|
| `LLMUnavailable` in `investigate` | Park. Checkpoint holds. `episode_tick` retries. **Never fabricate** |
| `LLMUnavailable` in `ask` while drafting | Send `probe.fallback_text` with `text_source='fallback'`. The question still goes out |
| `LLMUnavailable` in `critique` | Deterministic claim-to-source still runs. The LLM pass is skipped and recorded as skipped |
| Process dies mid-episode | The checkpoint is the state. The next `episode_tick` resumes from it |
| Two ticks overlap | Scheduler lock, `max_instances=1` |

The `ask` row is the important one: **the interruption does not depend on the model being up**,
because the authored fallback exists exactly for this.

---

## 7. Audit

Every node writes exactly one `audit_events` row, in the **same transaction** as its state write.

`control_tier` is set per row: `T1` for a tool call, `T2` for a draft, `T4` for a send. A tool call
outside the registry writes `permission_decision='denied'` and changes nothing.

`get_state_history()` is a debugging and inspection aid, **not** the audit record: replay
re-executes nodes rather than replaying cached results, so it is not a deterministic account of what
happened. The audit table is.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| A new flagged night while an episode is open | **Appended to that episode.** At most one non-closed episode per subject, asserted. Two would double-spend the budget and split the evidence |
| Answer arrives after the timeout resumed the graph | Ignored, logged. The episode already moved on |
| Answer arrives after the episode closed | Ignored, logged |
| The model emits a tool not in the registry | `PermissionDenied`, denied row, the loop continues without it |
| The model emits malformed JSON | One repair round, then `ValidationFailed` and the step aborts |
| The model loops on the same tool | `MAX_TOOL_CALLS_PER_EPISODE` catches it. Repeated identical calls are also deduped and returned from cache |
| Rung is `COLD` | The graph is never entered. Asserted at open |
| Human rejects the draft at review | `UNRESOLVED`, decision and rationale recorded |
| Human edits the draft | The edited text is stored, the machine fields are not overwritten, and the edit is recorded |

---

## 9. Tests

`tests/unit/agent/` and `tests/scenario/`. All run with `WHA_LLM_PROVIDER=cassette`.

| Test | Asserts |
|---|---|
| `test_graph_compiles_with_checkpointer` | |
| `test_preload_populates_cheap_context` | Five keys present before `investigate` runs |
| `test_investigate_can_still_call_preloaded_tool` | Preloading does not restrict |
| `test_tool_call_cap_terminates_investigation` | At `MAX_TOOL_CALLS_PER_EPISODE`, no exception |
| `test_unregistered_tool_is_denied` | No state change, `permission_decision='denied'` |
| `test_untrusted_text_produces_typed_output_only` | An injected instruction appears as a field value, never as an action |
| `test_interrupt_resume_does_not_double_send` | The node re-runs from the top and sends once |
| `test_interrupt_resume_is_idempotent_on_writes` | One interaction row, not two |
| `test_timeout_resumes_with_timed_out_answer` | And the policy still reaches a disposition |
| `test_non_response_reaches_a_disposition` | The designed path, not a hang |
| `test_llm_unavailable_parks_not_closes` | State intact, episode still `OPEN`, retried next tick |
| `test_llm_unavailable_in_ask_uses_fallback_text` | The question is still sent, `text_source='fallback'` |
| `test_recursion_limit_closes_unresolved` | `GraphRecursionError` is caught, not propagated |
| `test_second_flagged_night_extends_episode` | One episode, two nights, not two episodes |
| `test_only_one_open_episode_asserted` | Attempting a second raises |
| `test_veto_cannot_authorise` | A model attempting to authorise a declined ask is rejected |
| `test_every_node_writes_one_audit_row` | Count matches the node count |
| `test_audit_row_and_state_write_share_a_transaction` | A failure leaves neither |
| `test_cold_rung_never_enters_graph` | |

`tests/scenario/` runs each fixture end to end and asserts the expected disposition, whether it
asked, and whether it escalated.

---

## 10. Exit condition

```bash
uv run pytest tests/unit/agent tests/scenario -q
uv run wha demo run illness-onset
```

The demo completes an episode end to end against cassettes, with no network, and produces a
validated `EpisodeOutcome` matching the fixture's `expect` block.
