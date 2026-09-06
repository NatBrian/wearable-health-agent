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
