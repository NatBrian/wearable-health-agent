# Disclaimer

**This is not a medical device.**

This repository contains a research prototype and a personal wellness tool. It is not intended to
diagnose, treat, cure or prevent any disease, and it must not be used as a substitute for
professional medical advice, diagnosis or treatment.

It makes no claim of clinical validity. It has not been evaluated by any regulator, it has not been
prospectively validated, and its outputs carry uncertainty that is stated explicitly rather than
hidden. Anything clinically consequential is routed to a professional by deterministic code that the
language model cannot override, and `INSUFFICIENT_DATA` is a first-class outcome rather than an
error.

Always seek the advice of a qualified health provider with any question regarding a medical
condition. **If you have symptoms that concern you, contact a clinician or emergency services. Do not
wait for this system, and do not let its output delay you.**

The limits of what this system can and cannot determine are indexed in
[`docs/DISCLOSURES.md`](docs/DISCLOSURES.md), which lists every limitation, the evidence for it,
and **the screen it appears on**: a limitation that lives only in a markdown file is not disclosed
to the person using the system. They are part of the design, not caveats discovered afterwards.

Two of them are worth stating here rather than only there. **Eight of the ten numbers in the
deterministic safety floor have no published source**, and say so on **The record** screen. And a
sentence shown with a citation can still misdescribe the passage it cites: the check behind it
proves the quoted span exists in the source, not that the sentence around it is a fair reading, so
where the two differ **the passage is the one to believe**.

The original mechanism-level discussion is in [`archive/PROPOSAL.md`](archive/PROPOSAL.md) section
2.5, which is finished work and superseded in fourteen documented ways.
