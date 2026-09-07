"""Does search bring back passages about what was asked?

The grounding check proves a sentence came from a passage. It proves nothing about
whether the passage was relevant, and the Evidence tab labels what it shows "Knowledge
Citations and Evidence". So an irrelevant passage is presented to a person as the evidence
behind a conclusion about their health.

The review recorded three real failures: for an episode about fever, four of the five
passages shown were about stiff neck and the top one was the list of answer options for
the symptom question; and in a chest pain conversation the single source cited under an
urgent escalation was "How to Prevent Heart Disease".

The proposed fix, item 30 of the refinement plan, was a cross-encoder reranker: fetch the
top 20 candidates instead of the top 8, score each with a small cross-encoder such as
BAAI/bge-reranker-base, keep the best 8.

DECISION, 5 September 2026: MEASURED AND NOT ADOPTED.
=====================================================

Two things were measured, in this order, and the second only because of the first.

**1. The reported failures were caused by the passages, not by the ranking.** Item 31
rewrote the layer 3 passages, which until then were generated straight from YAML and
included raw match lists. The top hit for a fever episode used to be the answer options for
the symptom question. Layer 4 was rewritten the same way afterwards, for the same reason.
After both, precision at 8 over the twelve judged queries below is **77.1%** (it was 79.2%
between the two rewrites, which is the number the sweep below was run against), and
`wha corpus search fever` returns Fever itself first and no internal configuration at all.

**2. A cross-encoder was tried anyway, in 16 configurations, and not one beat that.**
Two models, candidate pools of 12 and 20, passage text with and without the title
prepended, and cross-encoder order both replacing the hybrid order and fused with it
through RRF:

    baseline, no reranker                                       79.2%

    cross-encoder/ms-marco-MiniLM-L-6-v2   best of 8 configs    79.2%   1.9 s/query
                                           the plan's config    69.8%   3.4 s/query
    BAAI/bge-reranker-base                 best of 8 configs    78.1%  11.5 s/query
                                           the plan's config    72.9%  21.4 s/query

The best any reranker managed was to **tie**, and only when fused with the ranking it was
supposed to improve. The plan's exact prescription, a pool of 20 reordered outright by the
cross-encoder, is **6.3 points worse than doing nothing** with bge and **9.4 points worse**
with MiniLM. A deeper pool was consistently worse
than a shallower one, which is the mechanism: 20 candidates give the cross-encoder more
off-topic material it can promote, and BM25's exact term match on a small topical corpus is
a stronger signal than a model trained on MS MARCO web passages.

A perfect reranker over the same pool of 20 would reach 94.8%, so the headroom is real.
Neither of these models captures any of it. Reproduce with `tools/rerank_sweep.py`;
the full sixteen-row table is `experiments/retrieval/sweep-results.txt`.

**One number in this file moved after the sweep, and it is stated rather than quietly
restated.** The 79.2% baseline and all 16 reranker runs were measured on the corpus as it
stood that morning. Layer 4, the probe-evidence passages, was then rewritten as prose for
the same reason layer 3 was: searching "fever" returned `- **none**: "Nothing unusual"`, an
option-id dump presented as clinical evidence. After that rewrite the same twelve queries
score **77.1%**. The 2.1 points went on probe passages surfacing MORE, because prose written
for a reader matches a reader's phrasing: "is contributing to the raised reading" now
matches "why was last night flagged". The reranker conclusion is unaffected, since every
model was compared against the corpus it was measured on, and re-tuning the judgement keys
to recover the points would be the rigging this file warns about twice.

**So this is a plan item closed by measurement rather than done.** Adopting it would have
cost 1.1 GB of weights and seconds per query, on a machine that had 182 MB removed the same
day for not earning its place, to make retrieval worse. Recorded here rather than silently
skipped.

**The judgements below are mine, not a study's**, and that is the limitation of this file.
"Is this passage about what I asked" is at least something a reader can check by looking,
which is not true of a clinical figure. They were widened once, after a first run scored
44.8%, because several keys were unfairly narrow: Ebola marked off-topic for "fever", heart
attack for breathlessness on walking. A rigged benchmark that argues for buying a model is
worse than no benchmark. The widened keys are what every percentage above is measured
against, and running this file reprints the current one rather than trusting this docstring.

    uv run python tools/retrieval_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from wha.constants import RETRIEVE_TOP_K
from wha.retrieve.knowledge_docs import get_default_index

# query -> substrings that make a returned passage on-topic.
#
# Deliberately generous: a passage counts as relevant if it is about the thing asked OR
# about a condition that presents that way. The question is whether search returns
# something a person would recognise as related, not whether it returns the ideal passage.
# WIDENED after a first run, because several keys were unfairly narrow and a rigged
# benchmark is worse than none. Ebola and infectious mononucleosis ARE relevant to "fever";
# heartburn is a classic chest pain mimic; a heart attack and an arrhythmia ARE relevant to
# breathlessness on walking; the confounder passages ARE part of why a night was flagged.
# Marking those as misses would have manufactured a case for buying a model.
JUDGED: dict[str, tuple[str, ...]] = {
    "fever": (
        "fever",
        "dengue",
        "influenza",
        "flu",
        "infection",
        "probe_symptoms",
        "ebola",
        "mononucleosis",
        "malaria",
        "sepsis",
        "meningi",
    ),
    "chest pain": (
        "chest",
        "angina",
        "heart attack",
        "cardiac",
        "coronary",
        "heartburn",
        "reflux",
        "costochondritis",
        "pericard",
        "pulmonary embol",
    ),
    "I fainted": (
        "syncope",
        "faint",
        "cardiac arrest",
        "dizz",
        "blood pressure",
        "arrhythmia",
        "vertigo",
        "diabetes",
        "hypoglyc",
        "seizure",
        "anemia",
        "anaemia",
    ),
    "I feel exhausted and achy": (
        "fatigue",
        "tired",
        "ache",
        "tier_b",
        "sleep",
        "influenza",
        "stress",
        "insomnia",
        "anemia",
        "anaemia",
        "flu",
        "myalgi",
    ),
    "sore throat": (
        "throat",
        "pharyngitis",
        "cold",
        "strep",
        "tonsil",
        "flu",
        "cough",
        "diphtheria",
        "mononucleosis",
        "probe_symptoms",
    ),
    "I have been vomiting all night": (
        "vomit",
        "nausea",
        "gastro",
        "tier_b",
        "dehydrat",
        "rotavirus",
        "cholera",
        "food",
        "norovirus",
        "cryptosporidio",
        "poisoning",
        "bleeding",
    ),
    "why was last night flagged": (
        "method_",
        "detection",
        "baseline",
        "threshold",
        "confounder_",
    ),
    "what is my baseline": ("method_", "baseline", "confounder_", "vitals"),
    "could this be from drinking": (
        "alcohol",
        "confounder_alcohol",
        "probe_alcohol",
        "drinking",
        "liver",
        "hangover",
    ),
    "I went for a hard run yesterday": (
        "exert",
        "exercise",
        "physical activity",
        "confounder",
        "sport",
        "fitness",
        "muscle",
        "probe_exertion",
        "method_",
    ),
    "I had a vaccination on Tuesday": (
        "vaccin",
        "immuni",
        "confounder_vaccination",
        "shot",
        "tetanus",
        "mumps",
        "measles",
        "flu",
        "covid",
    ),
    "shortness of breath when I walk": (
        "breath",
        "asthma",
        "copd",
        "lung",
        "tier_b",
        "heart",
        "arrhythmia",
        "anaphylaxis",
        "dizz",
        "anemia",
        "anaemia",
        "pulmonary",
    ),
}


def relevant(chunk_id: str, title: str, keys: tuple[str, ...]) -> bool:
    haystack = f"{chunk_id} {title}".lower()
    return any(key in haystack for key in keys)


def main() -> int:
    index = get_default_index()

    print("=" * 84)
    print(f"PRECISION AT {RETRIEVE_TOP_K}: how many returned passages are about what was asked")
    print("=" * 84)
    print("Judged by the query keys in this file, which are a person's judgement and not a")
    print("study's. An off-topic passage is one a reader would not recognise as related.")
    print()

    total_hits = 0
    total_returned = 0
    misses: list[str] = []

    for query, keys in JUDGED.items():
        results = index.query(query, top_k=RETRIEVE_TOP_K)
        hits = [r for r in results if relevant(r.chunk_id, r.title, keys)]
        total_hits += len(hits)
        total_returned += len(results)
        mark = "ok " if len(hits) == len(results) else "   "
        print(f"{mark} {query:<34} {len(hits)}/{len(results)}")
        for r in results:
            if not relevant(r.chunk_id, r.title, keys):
                misses.append(f"    {query:<34} -> {r.title[:52]}")

    print()
    print(f"  overall precision: {total_hits}/{total_returned} = {total_hits / total_returned:.1%}")
    print()

    if misses:
        print("=" * 84)
        print("OFF-TOPIC PASSAGES, which is what a reranker would be for")
        print("=" * 84)
        for line in misses:
            print(line)
        print()

    print("=" * 84)
    print("THE RERANKER WAS MEASURED AND NOT ADOPTED, 5 September 2026")
    print("=" * 84)
    print("Item 30 of the refinement plan said to fetch the top 20 candidates, score them")
    print("with a cross-encoder such as BAAI/bge-reranker-base, and keep the best 8. That")
    print("was tried, in 16 configurations across two models, and NOT ONE beat the number")
    print("above. The plan's own prescription was 6 to 9 points WORSE. See DECISION below.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
