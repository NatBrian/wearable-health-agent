"""What this system can and cannot do, said on screen rather than only in a file.

The repository has carried a DISCLAIMER.md since the beginning and nothing in the interface
ever showed it, so a person using the dashboard was never told it is not a medical device.
Every limit named here is a design decision with its reasoning and citation in docs/, not a
caveat discovered afterwards, and each is stated in the place a reader meets it as well as
here: the sleep window and naps on History, the alerting floor on Today.
"""

import streamlit as st

from wha.constants import (
    BASELINE_MIN_NIGHTS_PERSONAL,
    DETECT_PERSISTENCE_NIGHTS,
)


def render_disclaimer() -> None:
    """The standing disclaimer. Shown where a person lands, not buried in a file."""
    st.error(
        "**This is not a medical device.** It cannot diagnose anything, and it is not a "
        "substitute for medical advice. **If you have symptoms that worry you, contact a "
        "clinician or emergency services. Do not wait for this system.**"
    )

    with st.expander("What this system can and cannot do"):
        st.markdown(
            f"""
**What it does**

It watches your resting heart rate while you sleep. A rise that persists for
{DETECT_PERSISTENCE_NIGHTS} nights is investigated, and you may be asked one question if the
answer would genuinely change the picture.

**What it cannot do**

- **It needs {BASELINE_MIN_NIGHTS_PERSONAL} nights of your sleep before it can raise
  anything.** Until then it is comparing you to a typical adult rather than to you, so it
  watches and learns but does not alert.
- **It only looks for a raised heart rate.** A low one is usually fitness or good rest.
  Conditions that lower resting heart rate are not looked for.
- **It cannot detect sleep apnoea.** Something that raises your heart rate every single
  night becomes part of what it learns as your normal.
- **It ignores naps.** Only your main overnight sleep is measured.
- **It cannot see a fever, a cough, or anything you do not tell it.** It has one signal from
  your wrist and whatever you choose to answer.
- **It has never been tested in a clinical trial** and makes no claim of clinical validity.

The reasoning and the research behind each of these is in the project's `docs/` folder, and
the record of every decision it made about you is on the Audit page.
"""
        )
