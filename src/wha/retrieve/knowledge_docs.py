"""The corpus the agent retrieves from, rendered out of the knowledge a human authored.

Three layers, three sources, no new medical content anywhere:

- **Layer 2**, how a night is measured and what counts as a deviation, from
  ``constants.py``. The numbers are imported rather than retyped, so a passage cannot
  drift away from the constant it describes.
- **Layer 3**, when to seek care, from ``red_flags.yaml``. The deterministic safety floor
  is the only care-pathway guidance in this repository, and it was written by a human.
- **Layer 4**, the competing explanations for an elevation, from ``causes.yaml``, in
  :func:`wha.retrieve.corpus.generate_layer_4_confounder_docs`.

Layer 1, the MedlinePlus consumer-health bulk download named in ``sources.yaml``, is
absent. It has not been fetched, and writing consumer health text without it would be
inventing clinical content. The agent can therefore cite why a night was flagged, what
else could explain it, and the rule behind an escalation, and cannot cite general
information about a condition. Stated in ``docs/DISCLOSURES.md`` and on the dashboard.

Every figure below was checked against the paper it cites in September 2026. What held up,
what did not, and the four caveats carried in the passage text are recorded in
``docs/CORPUS-VERIFICATION.md``.
"""

from pathlib import Path
from typing import Any

import numpy as np
import yaml

from wha.constants import (
    BASELINE_MIN_NIGHTS_PERSONAL,
    BASELINE_PERSONAL_CITATION,
    DAYTIME_EXCLUSION_CITATION,
    DETECT_CITATION,
    DETECT_DIRECTION_NOTE,
    DETECT_PERSISTENCE_NIGHTS,
    DETECT_RED_BPM,
    DETECT_YELLOW_BPM,
    MIN_NOCTURNAL_MINUTES,
    NAP_EXCLUSION_CITATION,
    POP_PRIOR_RHR_MEAN_BPM,
    POP_PRIOR_RHR_SD_BPM,
    SLEEP_WINDOW_CITATION,
)
from wha.retrieve.models import CorpusDocument

RED_FLAGS_PATH = Path("data/knowledge/red_flags.yaml")
PROBES_PATH = Path("data/knowledge/probes.yaml")


def _load_red_flags(path: Path | None = None) -> dict[str, Any]:
    """Read the safety floor. Read-only: nothing in this module writes to it."""
    target = path if path is not None else RED_FLAGS_PATH
    if not target.exists():
        return {}
    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def generate_layer_2_method_docs() -> list[CorpusDocument]:
    """How a night is measured and what counts as a deviation, with the sources."""
    docs: list[CorpusDocument] = []

    docs.append(
        CorpusDocument(
            doc_id="method_detection_thresholds",
            title="What counts as an elevated night",
            layer=2,
            source_url="src/wha/constants.py",
            licence="Ours",
            metadata={"topic": "detection", "citation": DETECT_CITATION},
            text=(
                "# What counts as an elevated night\n\n"
                f"A night is called elevated when the resting heart rate measured during "
                f"sleep sits at least {DETECT_YELLOW_BPM:.0f} bpm above the person's own "
                f"baseline, and is called RED at {DETECT_RED_BPM:.0f} bpm above it. An "
                f"investigation opens only when {DETECT_PERSISTENCE_NIGHTS} consecutive "
                "nights are elevated and at least one of them is RED.\n\n"
                "## Where these numbers come from\n\n"
                f"{DETECT_CITATION}. That study reports 3 bpm as the threshold because, "
                "across its participants, the median fluctuation of the median of average "
                "overnight resting heart rate over three months was only three bpm, so a "
                "3 bpm move is the point at which a change stops looking like ordinary "
                "night-to-night variation. Its red state requires the overnight resting "
                "heart rate to be at least four bpm above the baseline on two consecutive "
                "nights.\n\n"
                "In a cohort of 3,318 participants of whom 84 were infected, that alerting "
                "system flagged 67 of the 84, which is 80 percent, with pre-symptomatic "
                "signals at a median of three days before symptoms began.\n\n"
                "## What is deliberately not looked for\n\n"
                f"{DETECT_DIRECTION_NOTE}\n\n"
                f"A night with fewer than {MIN_NOCTURNAL_MINUTES} minutes of measured "
                "sleep is not scored at all, because a reading taken over a fragment of a "
                "night is not comparable with one taken over a whole night."
            ),
        )
    )

    docs.append(
        CorpusDocument(
            doc_id="method_personal_baseline",
            title="The baseline is the person's own, not the population's",
            layer=2,
            source_url="src/wha/constants.py",
            licence="Ours",
            metadata={"topic": "baseline", "citation": BASELINE_PERSONAL_CITATION},
            text=(
                "# The baseline is the person's own, not the population's\n\n"
                f"Once {BASELINE_MIN_NIGHTS_PERSONAL} usable nights exist, the centre a "
                "night is compared against is the person's own median sleeping resting "
                "heart rate. Below that count nothing is flagged at all, because a median "
                "over one or two nights is noise.\n\n"
                "## Why seven, and why not blended\n\n"
                f"{BASELINE_PERSONAL_CITATION}. The same study that supplies the 3 and 4 "
                "bpm thresholds defines its baseline as the streaming median of average "
                "overnight resting heart rate for each individual, with no population "
                "blending, and reports that for over 80 percent of participants the "
                "proper baseline was observed after only seven nights.\n\n"
                "Applying thresholds derived that way to a centre pulled toward a "
                "population average is a category error. Someone whose true sleeping "
                "resting heart rate is 45 bpm would carry a permanent negative residual "
                "and need a rise far larger than any infection produces before anything "
                "was noticed; someone at 80 bpm would sit above the threshold while "
                "perfectly healthy.\n\n"
                "## The cold start\n\n"
                f"Before seven nights the estimate is shrunk toward a population mean of "
                f"{POP_PRIOR_RHR_MEAN_BPM} bpm with a standard deviation of "
                f"{POP_PRIOR_RHR_SD_BPM} bpm. That figure is an average of 525 adults "
                "wearing an Oura ring, reported in Bloomfield et al. 2024, PLOS Digital "
                "Health 3(4):e0000473. They were first-year university students, so it is "
                "a starting guess rather than a description of any particular person, and "
                "it stops mattering once the person's own nights arrive."
            ),
        )
    )

    docs.append(
        CorpusDocument(
            doc_id="method_night_window",
            title="Why the reading is taken from recorded sleep",
            layer=2,
            source_url="src/wha/constants.py",
            licence="Ours",
            metadata={
                "topic": "measurement_window",
                "citation": f"{NAP_EXCLUSION_CITATION}; {DAYTIME_EXCLUSION_CITATION}",
            },
            text=(
                "# Why the reading is taken from recorded sleep\n\n"
                "The night's number is computed over the sleep the watch actually "
                "recorded, not over a fixed clock window, and daytime naps are excluded "
                "rather than pooled with overnight sleep.\n\n"
                "## Why sleep rather than the whole day\n\n"
                "Daytime heart rate mostly measures what a person was doing. Standing up, "
                "coffee or a flight of stairs move it by tens of beats per minute, while "
                "an infection moves it by roughly 1.6 to 5. Sleep is the closest a wrist "
                "device gets to a controlled measurement: one posture, no volitional "
                "input, at roughly the same point in the day.\n\n"
                f"{DAYTIME_EXCLUSION_CITATION}, states that during sleep individuals are "
                "no longer affected by external stimuli and therefore enhanced reliability "
                "may exist for recordings that occur during sleep. That study is eleven "
                "adolescent endurance athletes, which is a narrow basis, and its own "
                "variability result is reported by its authors as contrary to what they "
                "expected. It is quoted here with that limitation attached.\n\n"
                "## Why naps are excluded\n\n"
                f"{NAP_EXCLUSION_CITATION}. Thirty-two adults, within-subjects, with "
                "polysomnography and ECG, comparing a daytime nap against a night of "
                "sleep. RR intervals were longer and heart rate lower during nighttime "
                "sleep than during the nap, in both stage 2 and slow wave sleep. Pooling "
                "the two would mix distributions with different means and bias a night's "
                "reading by however much the person happened to nap.\n\n"
                "## What the device can and cannot be trusted for\n\n"
                f"{SLEEP_WINDOW_CITATION} validated nocturnal resting heart rate and heart "
                "rate variability from consumer wearables against an ECG reference, over "
                "13 adults and 536 nights. Agreement ranged from good to poor depending on "
                "the device. The five devices tested were a Garmin Fenix 6, two "
                "generations of Oura ring, a Polar Grit X Pro and a Whoop 4.0. The watch "
                "this system reads was not among them, so its nocturnal accuracy has not "
                "been independently validated.\n\n"
                "Consumer sleep staging is also not polysomnography. A night whose staging "
                "is wrong yields a measurement window that is wrong, and there is no "
                "cross-check for that here."
            ),
        )
    )

    return docs


def generate_layer_3_escalation_docs(
    red_flags: dict[str, Any] | None = None,
) -> list[CorpusDocument]:
    """When to seek care, rendered from the deterministic safety floor.

    One document per tier A rule so that an escalation can cite the specific rule that
    fired, plus one each for the tier B set, the vital-sign bounds and the never-say list.
    """
    data = red_flags if red_flags is not None else _load_red_flags()
    docs: list[CorpusDocument] = []

    for rule in data.get("tier_a", []) or []:
        rule_id = rule.get("id", "rf_unknown")
        phrases = ", ".join(f'"{m}"' for m in rule.get("match", []))
        also = rule.get("requires_also")
        lines = [
            f"# Urgent sign: {rule_id}",
            "",
            (
                "This is a tier A sign. One match is enough, and it goes straight to an "
                "urgent escalation without passing through any reasoning about likelihood."
            ),
            "",
            "## What the person said",
            "",
            f"Any of: {phrases}.",
        ]
        if also:
            lines += [
                "",
                f"This rule alone is not enough. It fires only alongside: {', '.join(also)}.",
            ]
        lines += [
            "",
            "## What to do",
            "",
            str(rule.get("guidance", "")).strip(),
            "",
            "## Why this is on the urgent list",
            "",
            str(rule.get("rationale", "")).strip(),
        ]
        docs.append(
            CorpusDocument(
                doc_id=f"escalation_{rule_id}",
                title=f"Urgent sign: {rule_id}",
                layer=3,
                source_url="data/knowledge/red_flags.yaml",
                licence="Ours",
                text="\n".join(lines),
                metadata={"topic": "escalation", "tier": "A", "rule_id": rule_id},
            )
        )

    tier_b = data.get("tier_b", []) or []
    if tier_b:
        lines = [
            "# Signs worth a same-day appointment",
            "",
            (
                "These are tier B. Two or more together, or one that has not settled "
                "within the stated number of nights, is worth being seen the same day."
            ),
            "",
        ]
        for rule in tier_b:
            phrases = ", ".join(f'"{m}"' for m in rule.get("match", []))
            persist = rule.get("persist_nights")
            lines.append(
                f"- **{rule.get('id', 'rf_unknown')}**: {phrases}."
                + (f" Counts as persistent after {persist} nights." if persist else "")
            )
        guidance = str(data.get("tier_b_guidance", "")).strip()
        if guidance:
            lines += ["", "## What to do", "", guidance]
        docs.append(
            CorpusDocument(
                doc_id="escalation_tier_b",
                title="Signs worth a same-day appointment",
                layer=3,
                source_url="data/knowledge/red_flags.yaml",
                licence="Ours",
                text="\n".join(lines),
                metadata={"topic": "escalation", "tier": "B"},
            )
        )

    vitals = data.get("vitals", []) or []
    if vitals:
        lines = [
            "# When the reading itself is far outside the person's range",
            "",
            (
                "These bounds are expressed against the person's own baseline rather than "
                "as absolute heart rates, because a given number means different things "
                "for different people."
            ),
            "",
        ]
        for rule in vitals:
            above = rule.get("robust_z_above")
            below = rule.get("robust_z_below")
            bound = (
                f"{above} robust standard deviations above the person's usual"
                if above is not None
                else f"{below} robust standard deviations below the person's usual"
            )
            lines += [
                f"## {rule.get('id', 'rf_unknown')}",
                "",
                f"Fires at {bound}.",
                "",
                str(rule.get("guidance", "")).strip(),
                "",
                str(rule.get("rationale", "")).strip(),
                "",
            ]
            fallback_high = rule.get("cold_rung_fallback_bpm_above")
            fallback_low = rule.get("cold_rung_fallback_bpm_below")
            if fallback_high is not None:
                lines += [
                    (
                        "Before a personal range exists, a wide absolute bound of "
                        f"{fallback_high} bpm is used instead."
                    ),
                    "",
                ]
            if fallback_low is not None:
                lines += [
                    (
                        "Before a personal range exists, a wide absolute bound of "
                        f"{fallback_low} bpm is used instead."
                    ),
                    "",
                ]
        docs.append(
            CorpusDocument(
                doc_id="escalation_vitals",
                title="When the reading itself is far outside the person's range",
                layer=3,
                source_url="data/knowledge/red_flags.yaml",
                licence="Ours",
                text="\n".join(lines),
                metadata={"topic": "escalation", "tier": "vitals"},
            )
        )

    always = data.get("always", {}) or {}
    never_say = always.get("never_say", []) or []
    if never_say:
        docs.append(
            CorpusDocument(
                doc_id="escalation_never_say",
                title="What this system never says",
                layer=3,
                source_url="data/knowledge/red_flags.yaml",
                licence="Ours",
                metadata={"topic": "output_limits"},
                text=(
                    "# What this system never says\n\n"
                    "Regardless of what it concluded, including when it concludes that an "
                    "elevation was most likely benign, this system never tells anyone "
                    "they are fine. The following phrasings are refused outright: "
                    + ", ".join(f'"{p}"' for p in never_say)
                    + ".\n\n"
                    "Its set of conclusions includes 'unresolved' and 'not enough data', "
                    "and every conclusion carries explicit criteria for when to seek care "
                    "anyway. It is not a medical device and does not diagnose."
                ),
            )
        )

    return docs


def generate_probe_evidence_docs(path: Path | None = None) -> list[CorpusDocument]:
    """What an answer to each question actually tells us, from probes.yaml.

    This is the layer that makes re-investigating after an answer worth doing. Without it
    the corpus can say what an infection does to a heart rate but nothing about what the
    word "fever" implies, so an agent handed an answer has nothing to look up.

    Every likelihood row here is marked ASSUMED in the source file, and each passage says
    so. No published measurement exists of how accurately a person reports drinking,
    stress or symptoms to an app the next morning, and the honest thing is to carry that
    caveat into anything the agent cites rather than to let a cited number look measured.
    """
    target = path if path is not None else PROBES_PATH
    if not target.exists():
        return []
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []

    docs: list[CorpusDocument] = []
    for probe in data.get("probes", []) or []:
        if not isinstance(probe, dict):
            continue
        probe_id = str(probe.get("probe_id", "probe_unknown"))
        cause = str(probe.get("target_cause", "unknown"))
        answers = probe.get("answer_space", []) or []
        likelihood = probe.get("likelihood", {}) or {}
        present = likelihood.get("present", {}) or {}
        absent = likelihood.get("absent", {}) or {}
        labels = {str(a.get("option_id")): str(a.get("label", "")) for a in answers}

        lines = [
            f"# What an answer to {probe_id} tells us about {cause}",
            "",
            (
                f"This question exists to resolve one thing: whether {cause} is "
                "contributing to the elevation. The question wording is written fresh "
                "each time; only the answer slots are fixed, because the numbers below "
                "are defined over those slots."
            ),
            "",
            "## The answers offered",
            "",
        ]
        for option_id, label in labels.items():
            lines.append(f'- **{option_id}**: "{label}"')

        lines += [
            "",
            "## How much each answer moves the belief",
            "",
            (
                f"Probability of each answer if {cause} IS contributing, against the "
                "probability of the same answer if it is not:"
            ),
            "",
        ]
        for option_id, label in labels.items():
            p_present = present.get(option_id)
            p_absent = absent.get(option_id)
            if p_present is None or p_absent is None:
                continue
            lines.append(f'- "{label}": {p_present:.2f} if present, {p_absent:.2f} if absent.')

        provenance = str(probe.get("provenance", "")).strip()
        assumption = str(probe.get("assumption", "")).strip()
        lines += [
            "",
            "## How reliable these numbers are",
            "",
            (
                f"Provenance: {provenance or 'unstated'}. These are not measured values. "
                "No published study quantifies how accurately a person reports drinking, "
                "stress, sleep or early symptoms to an app when prompted the next "
                "morning, so this row is an explicit assumption, set deliberately flat so "
                "that it understates how informative the question is and the system "
                "interrupts less rather than more."
            ),
        ]
        if assumption:
            lines += ["", assumption]

        docs.append(
            CorpusDocument(
                doc_id=f"evidence_{probe_id}",
                title=f"What an answer to {probe_id} tells us about {cause}",
                layer=4,
                source_url="data/knowledge/probes.yaml",
                licence="Ours",
                text="\n".join(lines),
                metadata={
                    "topic": "probe_evidence",
                    "probe_id": probe_id,
                    "cause_id": cause,
                    "provenance": provenance,
                },
            )
        )

    return docs


def build_default_corpus(red_flags: dict[str, Any] | None = None) -> list[CorpusDocument]:
    """Every document the agent can retrieve and cite, in layer order."""
    from wha.retrieve.corpus import generate_layer_4_confounder_docs

    return [
        *generate_layer_2_method_docs(),
        *generate_layer_3_escalation_docs(red_flags),
        *generate_layer_4_confounder_docs(),
        *generate_probe_evidence_docs(),
    ]


class _BM25OnlyEmbedder:
    """Stands in when the dense model cannot be loaded, so retrieval degrades to BM25.

    The embedding model is a download. On a machine that has never fetched it and has no
    network, constructing the real embedder raises, and an exception there would leave
    ``retrieval_index`` None and the retrieval tool silently returning nothing, which is
    exactly the failure this work exists to remove. Returning no vectors makes
    :class:`HybridIndex` skip the dense half and rank on BM25 alone.
    """

    def embed_texts(self, texts: list[str]) -> "np.ndarray":
        return np.empty((0, 384), dtype=np.float32)


_INDEX_CACHE: dict[str, Any] = {}


def build_index(docs: list[CorpusDocument] | None = None) -> Any:
    """Chunk the corpus and build the hybrid index over it."""
    from wha.retrieve.chunking import chunk_document
    from wha.retrieve.index import DefaultSentenceTransformerEmbedder, HybridIndex

    corpus = docs if docs is not None else build_default_corpus()
    chunks = [chunk for doc in corpus for chunk in chunk_document(doc)]

    try:
        return HybridIndex(chunks, embedder=DefaultSentenceTransformerEmbedder())
    except Exception:  # noqa: BLE001
        # Deliberately broad. sentence-transformers surfaces network, filesystem and
        # torch errors of several unrelated types, and none of them is a reason to leave
        # the agent with no corpus at all.
        return HybridIndex(chunks, embedder=_BM25OnlyEmbedder())


def get_default_index() -> Any:
    """The shared index over the authored corpus, built once per process.

    Building it embeds every chunk, which costs seconds. It is built on first use rather
    than at import so that a command which never retrieves never pays for it.
    """
    index = _INDEX_CACHE.get("default")
    if index is None:
        index = build_index()
        _INDEX_CACHE["default"] = index
    return index
