# Why the phone screens are shaped as they are

The interface rules in spec section 6.2 are the product of reading, not
preference. Each source below has what was studied, what it found, which rule
it justifies, and whether it was read in full or located. None of these studied
this system, and these are interface rules, not clinical ones. Nothing here
justifies a medical claim.

## 1. Amershi et al. 2019

Amershi S, Weld D, Vorvoreanu M, et al. Guidelines for Human-AI Interaction.
CHI 2019. doi:10.1145/3290605.3300233. Read in full.

Eighteen guidelines in four phases of interacting with AI, validated with
forty-nine practitioners across twenty products. The relevant ones: say what
the system can do (G1) and how well it does it (G2); support efficient
correction (G8, G9); show contextually relevant information (G11); support
global controls (G17).

Justifies: the onboarding that states what the system can and cannot do before
first use, including that it has never been tested on a patient; one-tap
dismissal with free-text correction on every question; the quiet-reason card
that shows the reason on the screen where the person would look for it; the
Settings screen as the one place that controls everything.

## 2. Meng et al. 2026

Meng Y, Liu B, Liu Z, Chen R. Wearing Trust: How Older Adults Calibrate
Reliance on Health Wearables Through Bodily Experience and Everyday Use.
arXiv:2608.08856, 2026. Read in full.

Thirty-one interviews with older adults using health wearables. Names the
"observability gap": people judge a wearable by price, interface density and
bodily agreement because the system hides signal quality, uncertainty and
failure conditions. Calls for alert provenance: saying which machine raised
something and what it read.

Justifies: labelling every statement by which machine produced it
(arithmetic, rule, model, quoted source); showing signal quality on Today
(contact minutes, whether sleep was recorded, the rung and the nights behind
it, the last pull time); keeping dense interfaces honest rather than
impressive.

## 3. He et al. 2023

He X, Zheng X, Ding H. Existing Barriers Faced by and Future Design
Recommendations for Direct-to-Consumer Health Care Artificial Intelligence
Apps: Scoping Review. J Med Internet Res 2023;25:e50342. Read in full, results
and recommendations sections.

Thirty-two studies; eight barriers and six recommendations for consumer health
AI apps. The relevant recommendations: explain performance in plain words,
disclose progressively rather than all at once, and end with what the person
can act on.

Justifies: the capability statement in plain words; layered explanations (a
sentence, then the why, then the full trace on request); ending conclusions
with what to do next and where to seek help.

## 4. Islam et al. 2026

Islam F, Islam A, Amin MA, Zaber M. A Proposed Participatory Framework for
Explainable AI in mHealth: Mixed Methods Study Integrating User and
Stakeholder Requirements. J Med Internet Res 2026;28:e87158. Read in full,
results, framework and discussion sections.

A survey of 137 users plus twenty stakeholders, yielding a five-pillar
framework for explainable AI in mobile health. Its central finding: users did
not distinguish between apps by their algorithm; they wanted stepwise
cause-and-effect narratives and human validation, with human oversight as the
foundation (pillar 1) and layered, adaptive explanations (pillar 2).

Justifies: the Investigation screen telling cause and effect in sentences
before probabilities; the review checkpoint where a person approves, edits,
rejects or escalates, with the screen making clear the system did not act
alone.

## 5. Rojo et al. 2024

Rojo D, Lamqaddam H, Gosak L, Verbert K. Petal-X: Human-Centered Visual
Explanations to Improve Cardiovascular Risk Communication. arXiv:2406.18690,
2024. Read in full, sections 1 to 4.

Lay audiences preferred a flower-shaped contribution plot over score charts
for seeing which factor contributed how much to a cardiovascular risk reading.

Justifies: restraint with charts on the phone. The History chart shows one
measure against one band with words beside every colour, and probabilities sit
behind a narrative rather than leading it.

## What these do not cover

None of these studied this system, and none was run on the person using it.
They justify interface rules: how to show a reason, where to put a control,
what to label. They say nothing about whether any threshold, cause or
conclusion in this system is medically right. That question belongs to the
clinical sources in `data/knowledge/`, not to this file.
