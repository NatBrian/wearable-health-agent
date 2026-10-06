"""The corpus the agent retrieves from, rendered out of the knowledge tables here.

Four layers, four sources, no new medical content written anywhere:

- **Layer 1**, general consumer health information about a condition, from the MedlinePlus
  release fetched by :mod:`wha.retrieve.medlineplus`. Fetched, not authored, and not
  redistributed in this repository: which snapshot is in use is recorded with its checksum
  in ``data/knowledge/corpus-sources.json``. It is untrusted external text and is scanned
  for injection before the model sees it.
- **Layer 2**, how a night is measured and what counts as a deviation, from
  ``constants.py``. The numbers are imported rather than retyped, so a passage cannot
  drift away from the constant it describes.
- **Layer 3**, when to seek care, from ``red_flags.yaml``. The deterministic safety floor
  is the only care-pathway guidance in this repository.
- **Layer 4**, the competing explanations for an elevation, from ``causes.yaml``, in
  :func:`wha.retrieve.corpus.generate_layer_4_confounder_docs`.

The agent can therefore cite why a night was flagged, what else could explain it, the rule
behind an escalation, and general background on a condition. It still cannot search the web
and cannot write clinical text of its own. What it can and cannot look up is stated in
``docs/DISCLOSURES.md`` and on the dashboard.

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
    WITHIN_PERSON_SCALE_PRIOR_BPM,
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
                "nights are RED. That is the published rule exactly, and one RED night on "
                "its own never opens anything.\n\n"
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
                f"Before seven nights the centre is shrunk toward a population mean of "
                f"{POP_PRIOR_RHR_MEAN_BPM} bpm. That figure is an average of 525 adults "
                "wearing an Oura ring, reported in Bloomfield et al. 2024, PLOS Digital "
                "Health 3(4):e0000473. They were first-year university students, so it is "
                "a starting guess rather than a description of any particular person, and "
                "it stops mattering once the person's own nights arrive.\n\n"
                "The WIDTH of the band shrinks toward a different number, "
                f"{WITHIN_PERSON_SCALE_PRIOR_BPM} bpm, and the distinction matters. "
                f"The {POP_PRIOR_RHR_SD_BPM} bpm standard deviation in that same paper is "
                "how much 525 different people differ from EACH OTHER. The width of this "
                "band is how much ONE person differs from THEMSELVES between nights, "
                "which is a different and much smaller quantity. This system derives it "
                "from an archive of past wearable readings rather than from a clinical "
                "study. Using the first number for the second made every band about a "
                "third too wide."
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


# The passages are what a person READS. They used to be generated straight out of the YAML
# with the match lists in them, so somebody looking at the evidence behind an escalation was
# shown 'Any of: "stiff neck", "neck stiffness", "can't touch chin to chest"'. That is an
# internal keyword list presented as clinical evidence, and it publishes exactly which words
# cause an escalation, which is an invitation to phrase around them.
#
# The rule id stays in the metadata, so the audit trail still links a passage back to the
# rule that produced it. Only the phrase list is gone from the text.
_SIGN_TITLES: dict[str, str] = {
    "rf_chest_pain": "Chest pain or pressure",
    "rf_breathless_at_rest": "Breathlessness at rest",
    "rf_confusion": "New confusion",
    "rf_syncope": "Fainting or near-fainting",
    "rf_meningism": "A stiff neck with fever",
    "rf_bleeding": "Uncontrolled or unexplained bleeding",
    "rf_fever": "Fever",
    "rf_body_aches": "Body aches",
    "rf_severe_fatigue": "Severe fatigue",
    "rf_poor_intake": "Not eating or drinking",
    "rf_exertional_breathlessness": "Breathlessness on exertion",
    "rf_persistent_vomiting": "Repeated vomiting",
    # The two vitals rules. Missing, so the corpus printed "## rf_rhr_extreme_high" as a
    # section heading to a lay reader.
    "rf_rhr_extreme_high": "An overnight heart rate far above your own usual",
    "rf_rhr_extreme_low": "An overnight heart rate far below your own usual",
}


def _sign_title(rule_id: str) -> str:
    """A readable name for a rule, falling back to the id rather than inventing one."""
    return _SIGN_TITLES.get(rule_id, rule_id)


def _describe_phrases(matches: list[str]) -> str:
    """The words people use for this sign, as a sentence rather than a quoted list.

    The vocabulary has to survive: retrieval is what puts this passage in front of the
    agent when somebody writes "I fainted", and a test asserts that the authored safety
    rules are not swamped by a thousand MedlinePlus topics. Removing the words entirely
    broke that, which is exactly what the test is for.

    What changes is the presentation. It read `Any of: "stiff neck", "neck stiffness",
    "can't touch chin to chest"`, which is a configuration file shown as clinical
    evidence. The same words as a sentence read as health information.
    """
    phrases = [str(m).strip() for m in matches if str(m).strip()]
    if not phrases:
        return ""
    if len(phrases) == 1:
        return f"People describe this as {phrases[0]}."
    return "People describe this as " + ", ".join(phrases[:-1]) + f", or {phrases[-1]}."


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
        also = rule.get("requires_also")
        lines = [
            f"# {_sign_title(rule_id)}",
            "",
            (
                "This is an urgent sign. One report of it is enough, and it goes straight "
                "to an urgent escalation without passing through any reasoning about how "
                "likely anything is."
            ),
            "",
            "## What to do",
            "",
            str(rule.get("guidance", "")).strip(),
            "",
            "## Why this is on the urgent list",
            "",
            str(rule.get("rationale", "")).strip(),
        ]
        if also:
            lines += [
                "",
                "## When this one does not stand alone",
                "",
                "On its own this is usually something else. It is treated as urgent only "
                "alongside " + ", ".join(str(a) for a in also) + ".",
            ]
        described = _describe_phrases(rule.get("match", []))
        if described:
            lines += ["", "## How people describe it", "", described]
        docs.append(
            CorpusDocument(
                doc_id=f"escalation_{rule_id}",
                title=f"Urgent sign: {_sign_title(rule_id)}",
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
            persist = rule.get("persist_nights")
            described = _describe_phrases(rule.get("match", []))
            lines.append(
                f"- **{_sign_title(rule.get('id', 'rf_unknown'))}**"
                + (f", if it has not settled within {persist} nights." if persist else ".")
                # `_describe_phrases` already returns the whole sentence. This prepended
                # "People describe this as " to it and lowercased the first letter of what
                # it got, producing "People describe this as people describe this as fever,
                # feverish, ..." on every tier B bullet.
                + (f" {described}" if described else "")
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

    # The two care-pathway lines every outcome carries.
    #
    # Item 2 moved these into red_flags.yaml with the stated purpose "so the corpus can
    # cite it", and then no generator read them, so the sentences a person is most likely
    # to act on were the only care guidance in the system that could not be retrieved or
    # cited. They are shown on every episode regardless of disposition, including
    # LIKELY_BENIGN, which is the one a person is most likely to act on by doing nothing.
    guidance_lines = [
        str(line).strip()
        for line in (data.get("outcome_guidance", {}) or {}).get("default", []) or []
        if str(line).strip()
    ]
    if guidance_lines:
        lines = [
            "# When to seek care, whatever this system concluded",
            "",
            (
                "These two sentences are attached to every investigation this system "
                "closes, including the ones it concludes are probably nothing. They are "
                "selected from a fixed list and never written fresh, so no wording here "
                "was composed by a language model."
            ),
            "",
        ]
        lines += [f"- {line}" for line in guidance_lines]
        docs.append(
            CorpusDocument(
                doc_id="escalation_outcome_guidance",
                title="When to seek care, whatever this system concluded",
                layer=3,
                source_url="data/knowledge/red_flags.yaml",
                licence="Ours",
                text="\n".join(lines),
                metadata={"topic": "escalation", "tier": "outcome_guidance"},
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
                # The rule id was the heading: "## rf_rhr_extreme_high", shown to a
                # person as clinical evidence. Item 31's check is that the Evidence tab
                # reads like health information rather than a configuration file, and an
                # identifier as a section heading is the plainest possible failure of it.
                # The id stays in metadata, where the audit trail reads it.
                f"## {_sign_title(rule.get('id', 'rf_unknown'))}",
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

    # causes.yaml already carries a written label for every cause. Using it keeps one
    # phrase for a cause across the tables, the screen and the corpus.
    cause_labels: dict[str, str] = {}
    causes_path = target.parent / "causes.yaml"
    if causes_path.exists():
        causes_data = yaml.safe_load(causes_path.read_text(encoding="utf-8"))
        if isinstance(causes_data, dict):
            for row in causes_data.get("causes", []) or []:
                if isinstance(row, dict) and row.get("cause"):
                    cause_labels[str(row["cause"])] = str(row.get("label", row["cause"]))

    docs: list[CorpusDocument] = []
    for probe in data.get("probes", []) or []:
        if not isinstance(probe, dict):
            continue
        probe_id = str(probe.get("probe_id", "probe_unknown"))
        cause = str(probe.get("target_cause", "unknown"))
        cause_label = cause_labels.get(cause, cause.replace("_", " "))
        answers = probe.get("answer_space", []) or []
        likelihood = probe.get("likelihood", {}) or {}
        present = likelihood.get("present", {}) or {}
        absent = likelihood.get("absent", {}) or {}
        labels = {str(a.get("option_id")): str(a.get("label", "")) for a in answers}

        # Item 31 rewrote layer 3 to stop it printing internal lists. This layer had the
        # same defect and it is the one the review actually complained about: searching
        # "fever" used to return this passage FIRST, and what it showed was
        # `- **none**: "Nothing unusual"`, an option-id dump presented as clinical
        # evidence. The ids live in metadata, where the audit trail reads them.
        question = str(probe.get("fallback_text", "")).strip()
        choices = [label for label in labels.values() if label]
        if len(choices) > 1:
            offered = ", ".join(choices[:-1]) + ", or " + choices[-1]
        else:
            offered = choices[0] if choices else "nothing"

        lines = [
            f"# Why this system asks about {cause_label}",
            "",
            (
                f"This question exists to resolve one thing: whether {cause_label.lower()} "
                "is contributing to the raised reading. The wording is written fresh each "
                "time, so it will not arrive in the same words twice, but the choices "
                "offered are fixed because the numbers below are defined over them."
            ),
            "",
            "## What you are asked, and what you can answer",
            "",
        ]
        if question:
            lines.append(f"The question is along the lines of: {question}")
            lines.append("")
        lines.append(f"The answers offered are: {offered}.")

        lines += [
            "",
            "## How much each answer moves the belief",
            "",
            (
                f"Probability of each answer if {cause_label.lower()} IS contributing, "
                "against the probability of the same answer if it is not:"
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
                title=f"Why this system asks about {cause_label}",
                layer=4,
                source_url="data/knowledge/probes.yaml",
                licence="Ours",
                text="\n".join(lines),
                metadata={
                    "topic": "probe_evidence",
                    "probe_id": probe_id,
                    "cause_id": cause,
                    "provenance": provenance,
                    "retrieval_phrases": [question, *choices],
                },
            )
        )

    return docs


def build_default_corpus(red_flags: dict[str, Any] | None = None) -> list[CorpusDocument]:
    """Every document the agent can retrieve and cite, in layer order.

    Layer 1 is MedlinePlus, and it is present only if a release has been fetched. Its
    absence is not an error: everything else here is authored in this repository and works
    without it. What must not happen is the agent quietly answering a question about a
    condition from the model's own knowledge because the layer is missing, so the absence
    is disclosed to the person rather than papered over.
    """
    from wha.retrieve.corpus import generate_layer_4_confounder_docs
    from wha.retrieve.medlineplus import load_local

    return [
        *load_local(),
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


# Embedding the corpus is the slow part of starting up, and it is pure of side effects:
# the same chunks always produce the same vectors. Adding MedlinePlus took the corpus from
# 133 chunks to about 1,850, which is not something to recompute on every process start.
#
# The cache is keyed on a digest of the chunk text itself, so it invalidates automatically
# when the corpus changes and can never serve vectors for text that is no longer there.
EMBEDDING_CACHE = Path("data/corpus/embeddings.npz")


def _corpus_digest(chunks: list[Any]) -> str:
    """A fingerprint of exactly this corpus, in this order."""
    import hashlib

    hasher = hashlib.sha256()
    for chunk in chunks:
        hasher.update(chunk.chunk_id.encode("utf-8"))
        hasher.update(chunk.text.encode("utf-8"))
    return hasher.hexdigest()


def _load_cached_embeddings(chunks: list[Any]) -> "np.ndarray | None":
    """Vectors for this exact corpus, or None when it has changed or none were stored."""
    if not EMBEDDING_CACHE.exists():
        return None
    try:
        stored = np.load(EMBEDDING_CACHE, allow_pickle=False)
        if str(stored["digest"]) != _corpus_digest(chunks):
            return None
        vectors = stored["embeddings"]
        if len(vectors) != len(chunks):
            return None
        return vectors
    except Exception:  # noqa: BLE001
        # A corrupt or unreadable cache is a reason to recompute, never a reason to fail.
        return None


def _save_cached_embeddings(chunks: list[Any], embeddings: "np.ndarray") -> None:
    """Store vectors beside their fingerprint. Best effort."""
    try:
        EMBEDDING_CACHE.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            EMBEDDING_CACHE,
            digest=np.array(_corpus_digest(chunks)),
            embeddings=embeddings,
        )
    except Exception:  # noqa: BLE001
        return


_INDEX_CACHE: dict[str, Any] = {}


def build_index(docs: list[CorpusDocument] | None = None) -> Any:
    """Chunk the corpus and build the hybrid index over it."""
    from wha.retrieve.chunking import chunk_document
    from wha.retrieve.index import DefaultSentenceTransformerEmbedder, HybridIndex

    corpus = docs if docs is not None else build_default_corpus()
    chunks = [chunk for doc in corpus for chunk in chunk_document(doc)]

    cached = _load_cached_embeddings(chunks)

    try:
        embedder = DefaultSentenceTransformerEmbedder()
        index = HybridIndex(chunks, embedder=embedder, embeddings=cached)
    except Exception:  # noqa: BLE001
        # Deliberately broad. sentence-transformers surfaces network, filesystem and
        # torch errors of several unrelated types, and none of them is a reason to leave
        # the agent with no corpus at all.
        return HybridIndex(chunks, embedder=_BM25OnlyEmbedder())

    if cached is None:
        _save_cached_embeddings(chunks, index.embeddings)
    return index


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
