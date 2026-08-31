# Component 13. LLM client

**Phase:** B. **Module:** `src/wha/llm/`. **Depends on:** nothing.

Provider-agnostic, cassette-first, and built on the assumption that **the endpoint is usually
down**.

---

## 1. Three providers, one interface

```python
class LLMClient(Protocol):
    def complete(self, prompt: Prompt, schema: type[BaseModel],
                 temperature: float, max_tokens: int) -> tuple[BaseModel, LLMUsage]: ...
```

| Provider | Path | Use |
|---|---|---|
| `cassette` | recorded responses on disk | **The default. Every test.** |
| `ollama_native` | `/api/chat` | The self-hosted endpoint. **The only path where `"think": false` works** |
| `openai_compatible` | `/v1/chat/completions` | OpenRouter, OpenAI, Together, Groq, vLLM, and a local Ollama |

One switch, `WHA_LLM_PROVIDER`.

**Development and any human-run command use `openai_compatible`** against the endpoint configured in
`.env`, currently `deepseek-v3.2`. It has a stable URL and key, so the ephemeral-tunnel problem the
design was originally built around no longer applies.

**`pytest` always uses `cassette`**, forced by an autouse fixture that overrides `.env`. That is not
a preference. 67 unattended tasks run the suite hundreds of times, and a live provider would
make that slow, costly, and nondeterministic enough to break every frozen scenario assertion.

`ollama_native` remains supported for a self-hosted model, and is the only path where
`"think": false` works. **Any OpenAI-compatible provider works**, which makes "bring your own model"
a product feature and a privacy answer rather than a fallback.

---

## 2. Structured output, and why the provider is never trusted

**Always request JSON. Always validate with Pydantic. One repair round. Then raise.**

```python
raw = provider.call(...)
try:
    return schema.model_validate_json(raw)
except ValidationError as e:
    repaired = provider.call(repair_prompt(raw, e, schema))   # exactly LLM_REPAIR_ATTEMPTS
    return schema.model_validate_json(repaired)               # a second failure raises
```

JSON mode is not uniform. Ollama has one; OpenAI-compatible providers vary in whether they honour
`response_format`, and some accept the parameter and ignore it. **Validation belongs in the
application layer, never in the model.**

A `ValidationFailed` writes `validation_status='failed'` to the audit row and aborts that step. It
does not retry forever and it does not fall back to parsing prose.

---

## 3. Traps that fail silently

| Trap | Rule |
|---|---|
| **Thinking models** | `max_tokens` below `LLM_MAX_TOKENS_FLOOR` returns `finish_reason="length"` with an **empty string**, not an error. Reasoning tokens are billed against the budget and stripped from `content`. A two-word answer has cost 37 completion tokens. **Never budget below the floor** |
| **Thinking toggle** | `"think": false` exists only on the native `/api/chat`. Setting it on `/v1/chat/completions` is silently ignored |
| **Endpoint stability** | The configured OpenAI-compatible endpoint has a **stable URL and key**, so the ephemeral-tunnel problem the design was originally built around no longer applies. Still read from `.env` at run time; never hard-code, never commit |
| **Not every model is a thinking model** | The configured `deepseek-v3.2` returns `finish_reason: stop` on short answers and does not burn hidden reasoning tokens. **The `max_tokens` floor stays global anyway**, because it costs nothing and the next model might |
| **Empty content with a 200** | Treat as `LLMUnavailable`, not as a valid empty answer |

The first row is the one that looks like a broken model and is not.

---

## 4. Cassettes

**Keyed on `(prompt_id, scenario)`, not on a hash of the inputs.** Scenarios are deterministic, so
the scenario name is a stable key that can be authored ahead of the implementation. A hash key
cannot be, because nobody knows the hash until the prompt renderer exists, and that would make every
cassette unwritable until the last moment.

```
tests/fixtures/llm_cassettes/<prompt_id>/<scenario>.json    scenario-specific
tests/fixtures/llm_cassettes/<prompt_id>/default.json       fallback for any scenario
```

```json
{
  "prompt_id": "write_question",
  "prompt_version": "1",
  "scenario": "illness-onset",
  "origin": "AUTHORED_FIXTURE",
  "model_id": "authored-fixture",
  "response": { "text": "...", "option_labels": ["..."], "rationale": "..." },
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0}
}
```

### Resolution order

1. `<prompt_id>/<scenario>.json` if a scenario context is set
2. `<prompt_id>/default.json`
3. **Hard failure**, naming the `prompt_id`, the scenario, and the path it looked for

**A miss never falls through to a live call.** A test that silently reaches the network is worse than
a failing one.

The scenario name comes from `WHA_SCENARIO`, set by `wha demo run` and by the scenario test
fixtures. When it is unset, only `default.json` is consulted.

### `investigate` is a list

The investigation loop makes several calls, so `investigate/<scenario>.json` holds a **list** of
responses consumed in order. Running past the end of the list yields a `Done`, which terminates the
loop cleanly rather than raising.

### `origin`, and the honesty this preserves

| `origin` | Meaning |
|---|---|
| `AUTHORED_FIXTURE` | Written by hand so the suite and the demo run with no endpoint and no human step. **Not a recording, and it does not evidence model behaviour** |
| `RECORDED` | Captured from a real endpoint by `uv run wha llm record --scenario <name>` |

Both are committed. Every audit row records which one produced the output, and the demo trace shows
`model_id: authored-fixture` rather than pretending a model was consulted.

> **What an authored fixture is and is not for.** It makes the pipeline runnable and the scenario
> assertions meaningful, because those assert on the **deterministic** parts: disposition, whether
> it asked, budget spent, claims stripped. It says nothing about how well a real model phrases a
> question. **No claim about model quality may rest on an authored fixture**, exactly as no
> performance claim may rest on synthetic data.

Re-recording against the live endpoint is task **B-27** and is **optional**. It is now genuinely
easy, because the endpoint is stable rather than ephemeral, but the system is fully demonstrable
without it.

---

## 5. Prompts

Files under `src/wha/llm/prompts/`, one per job, each carrying **all six components**: instruction,
context, output schema, constraints, examples, and **refusal conditions**.

**Refusal conditions are never optional.** They are what makes `INSUFFICIENT_DATA` reachable in
practice rather than only in the type system.

Each file declares `prompt_id` and `prompt_version`, both written to every audit row, so any output
traces to the exact specification that produced it. **Prompts are versioned system components: a
prompt edit is a behaviour change and re-runs the full regression suite.**

| `prompt_id` | Job | Temperature | Output |
|---|---|---|---|
| `investigate` | Choose the next tool call, or stop | `TEMP_DETERMINISTIC` | `ToolCall \| Done` |
| `extract_facts` | Structured facts from free text | `TEMP_DETERMINISTIC` | `list[ExtractedFact]` |
| `red_flag_check` | Additive safety classification | `TEMP_DETERMINISTIC` | `set[FlagId]` |
| `veto_check` | May this authorised ask be cancelled as redundant | `TEMP_DETERMINISTIC` | `VetoVerdict` |
| `write_question` | Phrase the selected probe | `TEMP_NATURAL` | `QuestionDraft` |
| `interview_followup` | The next question inside an open conversation | `TEMP_NATURAL` | `QuestionDraft` |
| `write_outcome` | The explanation prose | `TEMP_NATURAL` | `OutcomeDraft` |
| `critique` | Coherence pass, may only strip | `TEMP_DETERMINISTIC` | `CritiqueVerdict` |
| `answer_about_episode` | Grounded follow-up Q&A | `TEMP_NATURAL` | `GroundedAnswer` |

**Zero for anything checked, 0.3 for anything read.** A check that varies is not a check. Tool
selection is deterministic so cassette replay is exact.

---

## 6. Context assembly

The window is a budget shared by input and output, content past the limit is **silently truncated**,
and material in the middle is used less reliably than at the edges.

Therefore: select and compress before sending, never pass a full history dump, retrieve the few
relevant passages rather than the corpus, and **put the instruction and the most critical evidence at
the edges**.

A prompt exceeding its budget raises rather than truncating. Silent truncation is how a model ends up
reasoning about half a case without anyone knowing.

---

## 7. Unavailability

**The endpoint being down is the expected state, not an incident.**

```python
class LLMUnavailable(WhaError): ...   # timeout, connection error, auth failure, empty 200
```

| Where it happens | What the caller does |
|---|---|
| `investigate` | Park the episode. Checkpoint holds. Retry next `episode_tick` |
| `write_question` | Send `probe.fallback_text` with `text_source='fallback'`. **The interruption still happens** |
| `red_flag_check` | Rules alone decide. The skip is recorded. **Never blocks an escalation** |
| `critique` | Deterministic grounding still runs. The LLM pass is recorded as skipped |
| `write_outcome` | Park. An outcome is not urgent |

**It never fabricates a response and never closes an episode.** Every one of those behaviours is a
named test.

No automatic retry loop inside the client. One attempt, one timeout of `LLM_TIMEOUT_SECONDS`, then
raise. Retry policy belongs to the scheduler, which knows about time; the client does not.

---

## 8. Usage accounting

Every call records `model_id`, `prompt_id`, `prompt_version`, `latency_ms` and token usage on the
audit row. Cost and latency per episode are reported in the evaluation, because "the LLM is never
invoked on a quiet night" is a **measurable claim**, and the number of quiet nights with zero calls
is the evidence for it.

---

## 9. Edge cases

| Case | Behaviour |
|---|---|
| 200 with empty content | `LLMUnavailable`, not a valid answer |
| `finish_reason="length"` | `LLMUnavailable` with a note naming the budget. Almost always the floor trap |
| Valid JSON, wrong schema | One repair round, then `ValidationFailed` |
| Provider returns markdown-fenced JSON | Strip a single fence before parsing. Beyond that, repair |
| Cassette missing in a test | Hard failure naming the key and the record command |
| Cassette present but `prompt_version` differs | Hard failure. **A stale cassette is worse than none** |
| Two threads call at once | Independent clients, no shared state |
| Model returns a tool name not in the registry | Component 10 denies it. The client does not validate tool names |

---

## 10. Tests

`tests/unit/llm/`. **No test reaches the network.**

| Test | Asserts |
|---|---|
| `test_cassette_provider_is_default` | Unset config gives `cassette` |
| `test_cassette_miss_fails_loudly` | Names the key and the record command |
| `test_stale_cassette_version_fails` | A version mismatch does not silently pass |
| `test_max_tokens_floor_enforced` | A call below the floor raises before it is sent |
| `test_empty_content_is_unavailable` | A 200 with `""` raises `LLMUnavailable` |
| `test_finish_reason_length_is_unavailable` | With the budget named |
| `test_one_repair_round_then_raises` | Exactly two calls, then `ValidationFailed` |
| `test_markdown_fence_stripped` | |
| `test_never_trusts_provider_schema` | A provider returning wrong-shaped JSON is caught |
| `test_think_false_only_on_native_path` | Not sent on the OpenAI-compatible path |
| `test_prompt_has_all_six_components` | Every prompt file. **A structural test over the directory** |
| `test_every_prompt_has_refusal_conditions` | Separately, because it is the one usually omitted |
| `test_temperature_zero_for_checked_jobs` | Extraction, red-flag, veto, critique, investigate |
| `test_prompt_version_written_to_audit` | |
| `test_oversize_prompt_raises_not_truncates` | |
| `test_unavailable_does_not_fabricate` | The caller receives an exception, never a plausible object |

---

## 11. Exit condition

```bash
uv run pytest tests/unit/llm -q
uv run wha doctor            # reports provider and cassette count
```

Green with `WHA_LLM_PROVIDER=cassette` and no network access at all.
