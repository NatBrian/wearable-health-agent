# Driving the rewritten dashboard, 6 September 2026

Every screen opened in a real browser through the Playwright MCP tools, against `uv run wha
serve` on the `sim` database, with the full suite green throughout.

**Findings are written down before any of them is fixed.** Fixing while walking is how a
walkthrough ends with three findings instead of eight.

---

## First pass

### 1. Every screen except Home showed a different person. Serious.

Opening `/Today`, `/History`, `/Audit` or `/Settings` directly showed subject `me`, which
holds four nights of the user's real data, while Home showed `sim`. Home reads the
configured subject when it builds its selector; the other four pages fell back to
`subjects[0]`, which is whichever row the database returns first.

The status bar made the disagreement visible without explaining it: Home said "28 nights
measured" and Today said "3 nights measured" for what a reader would assume is the same
person.

In a single-user health system this is the most serious finding here. A dashboard must
never quietly show one person's readings while another is selected.

### 2. The History chart drew the wrong colours and merged two legends. Serious.

The chart has two colour scales: one naming the lines, one colouring each night's dot by
what the system concluded. Vega-Lite merges legends for channels encoding the same field,
so both collapsed into a single block titled "What each line means, What ..." and the dot
swatches took their colours from the line palette: GREEN rendered blue, RED rendered blue,
YELLOW and NA rendered amber.

A chart that shows a RED night in the same colour as the line labelled "your sleeping heart
rate" is not a cosmetic problem. It is the screen making a false statement about the data,
and it is the same class of defect the previous chart's comments already recorded.

### 3. The pipeline opened on a night with no reading.

The night stepper defaults to the most recent night in the window. On both subjects that is
often a night the watch did not measure, so the first thing a reader sees is twenty steps
reading "did not run" and a headline of NA. The default should be the most recent night
there is something to explain.

### 4. Every step drew a card and then a button repeating it.

Each of the twenty steps rendered a styled card followed by a full-width button carrying
the same text, so the grid read every step name twice. The card is the thing to look at;
the button only needs to be the thing to press.

### 5. The status bar named something that is not on it.

When the system has recorded errors in the last day, the attention line read "Some parts of
the system need attention: Watch data, Problems today", and there is no line called
"Problems today" among the five. The sentence pointed at something the reader cannot find.

### 6. Home said the same sentence twice.

The urgent block rendered "If you feel unwell now. If you feel unwell now, contact a
clinician ...". The heading and the copy both opened with the same clause.

### 7. Home's honesty note counted the wrong thing.

It said "11 figures in this system's knowledge currently have no published source". The
endpoint returns twenty entries, one per cause and per probe, not a list of figures, and
eleven is only the count whose provenance is ASSUMED. Three more entries are DERIVED while
still carrying a figure with no source, so the true count of entries resting on an
unevidenced number is fourteen of twenty. The sentence was wrong twice: wrong unit, and an
undercount.

### 8. The same screen has two names.

The sidebar calls it "Audit", the page title calls it "The record", and Home's navigation
card calls it "Record". A reader following the Home card looking for "Record" finds
"Audit".

---

## What was fixed, and how each was checked

| # | Fix | Test that fails without it |
|---|---|---|
| 1 | Every page resolves the subject from the application's configured subject, never from the first row of a list | `tests/ui/test_shell.py::test_every_page_defaults_to_the_configured_subject` |
| 2 | The dot colours use `fill` with their own legend, so the two scales cannot merge | `tests/ui/test_history.py::test_the_two_colour_scales_do_not_merge_into_one_legend` |
| 3 | The stepper defaults to the most recent night with a reading | `tests/ui/test_audit_pipeline.py::test_the_stepper_opens_on_a_night_there_is_something_to_explain` |
| 4 | The button carries a short "Open" label; the card carries the name | `tests/ui/test_audit_pipeline.py::test_every_step_the_service_returns_is_drawn` |
| 5 | Recorded errors get their own line rather than being named in the attention list | `tests/ui/test_shell.py::test_the_attention_line_only_names_lines_that_are_on_screen` |
| 6 | Copy no longer repeats the heading | covered by the never-say sweep plus reading it |
| 7 | Counts entries carrying an unevidenced figure, and says entries | `tests/ui/test_shell.py::test_the_honesty_note_counts_entries_that_rest_on_an_unevidenced_figure` |
| 8 | One name everywhere: "The record" | `tests/ui/test_shell.py::test_the_record_screen_has_one_name` |

---

## Second pass

Server stopped and restarted, browser context closed and reopened, session state empty, every
screen walked again.

**The eight findings above are gone.** Opening `/Today` directly now shows `sim`, the same
person as Home, with the same night count. The sidebar, the page title and Home's card all
say "The record". The pipeline opens on 6 September, a night with a reading, rather than on
an unmeasured one. The attention line names only lines that are on the screen. The step grid
says each step name once. The chart legend separates the lines from the night colours.

Two things were checked by using them rather than by reading them:

* A citation chip in the chat opened the full MedlinePlus passage, with its attribution and
  its identifier, inside the conversation.
* The pipeline detail panel filled with what the selected step did, why it exists and its
  raw record.

### 9. One new finding, and it was only visible in the real app

"Nothing needs you right now" was drawn directly above a night the system had judged RED,
with an open investigation underneath it saying "the system is working through this now".

Nothing about that is technically wrong: nothing was waiting for the person to answer. But
on a health screen, a reassurance sitting above a red verdict is read as a verdict on the
person. It now says "Nothing is waiting for you to answer right now", which is what it
actually knows.

Fixed, with `tests/ui/test_today.py::test_the_reassurance_is_about_the_inbox_not_about_health`,
and re-checked in the browser.

---

## What the walkthrough is worth

Eight of the nine findings were invisible to a green suite, and the two most serious of them
were invisible to reading the code as well. The wrong-subject defect looked correct in every
test because every test supplies one subject. The chart's merged legend was a false statement
about the data that no assertion in the suite could have caught, because the suite did not
look at what colour anything was drawn in.


---

## Reported by the user after the second pass

### 10. The record screen showed two competing numbered lists of steps

"This night, step by step" numbered twenty steps in the order the system runs them.
"How this works" numbered eight sections, also from one, with different names, a different
order and a different count. Both read as "the steps", so the screen let a reader conclude
the system does two different things. This is the two-vocabularies defect the repository has
been bitten by before, reintroduced by carrying the old explainer across unchanged.

The eight sections are topics, not steps, and their own numbering was what made them look
like a rival list. They keep their content, which is worth keeping because every figure in
them is read from the running system, but each is now titled by the steps it covers:
"Reading the watch (steps 1 to 4)", "Working out the likely cause (step 11)".

`TOPIC_STEPS` in `wha/ui/components/how_it_works.py` holds that mapping, and
`tests/ui/test_audit_record.py::test_the_two_tabs_describe_one_system_not_two` asserts it
covers all twenty steps and claims none that do not exist, so a step added to the pipeline
cannot go unexplained and this page cannot invent one.

Found by the user reading the screen, not by the suite, and not by either of my own passes.


### 11. The topics were numbered against the steps but did not run in step order

Reported by the user after finding 10 was fixed. Titling each topic by the steps it covered
made a second problem visible rather than creating it: the ranges jumped about. Steps 19 and
20 sat fourth in the list, one topic claimed 8 to 10 and 15 to 18 with three other topics in
between, step 18 appeared under two topics, and nothing named 15 to 17 at all.

That was the old explainer's order carried across without being reconciled. There was no
reason for it beyond history. The topics now run in the order the steps run, each covering a
contiguous block, and the block that nothing explained, writing the conclusion and checking
it before you see it, is written.

`tests/ui/test_audit_record.py::test_the_topics_run_in_the_same_order_as_the_steps` asserts
each range is contiguous, that the ranges are in ascending order, and that no step is
explained twice.

"Where your data goes" is deliberately not a step and now says so, because it is true of all
of them.

### 12. Two buttons on Today opened the same screen

The verdict card offered "Show me how this was worked out" and the investigation card
offered "Show me every step of this". Both opened the record screen on the same night
whenever the investigation covered last night, which is the usual case.

One control survives, on the verdict card, labelled for what it opens: "See every step of
this night". The investigation card now says what the verdict card cannot, which is the span
of nights the investigation covers, phrased for one night or several.

`tests/ui/test_today.py::test_one_control_opens_the_pipeline_not_two` asserts there is
exactly one.
