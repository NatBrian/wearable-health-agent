"""The consumer health layer: parsing, provenance, and not swamping our own rules."""

from pathlib import Path

import pytest

from wha.retrieve.medlineplus import (
    MIN_SUMMARY_CHARS,
    parse_topics,
    resolve_latest_url,
)

_SAMPLE = b"""<?xml version="1.0"?>
<health-topics>
  <health-topic id="999" title="Fever" url="https://medlineplus.gov/fever.html"
                language="English">
    <also-called>Pyrexia</also-called>
    <full-summary>&lt;p&gt;A fever is a &lt;b&gt;body temperature&lt;/b&gt; that is higher
      than normal. It is not an illness in itself. It is usually a sign that your body is
      fighting an infection of some kind, and it will often settle on its own without any
      treatment being needed by anybody at all.&lt;/p&gt;</full-summary>
    <group>Symptoms</group>
    <mesh-heading><descriptor>Fever</descriptor></mesh-heading>
  </health-topic>
  <health-topic id="998" title="Fiebre" url="https://medlineplus.gov/spanish/fever.html"
                language="Spanish">
    <full-summary>La fiebre es una temperatura corporal mas alta de lo normal y suele ser
      una senal de que el cuerpo esta combatiendo una infeccion de algun tipo.</full-summary>
  </health-topic>
  <health-topic id="997" title="Stub" url="https://medlineplus.gov/stub.html"
                language="English">
    <full-summary>Too short.</full-summary>
  </health-topic>
</health-topics>
"""


def test_the_newest_dated_snapshot_is_resolved_not_hardcoded() -> None:
    """The URL in sources.yaml was a 404 and appears never to have existed.

    MedlinePlus publishes dated snapshots. Resolving the newest one at fetch time means the
    entry cannot rot again, and means the snapshot in use is a recorded fact.
    """
    html = """
      <a href="https://medlineplus.gov/xml/mplus_topics_compressed_2026-08-27.zip">old</a>
      <a href="https://medlineplus.gov/xml/mplus_topics_compressed_2026-09-03.zip">new</a>
      <a href="https://medlineplus.gov/xml/mplus_topics_compressed_2026-09-01.zip">mid</a>
    """
    url, date = resolve_latest_url(html)

    assert date == "2026-09-03"
    assert url.endswith("mplus_topics_compressed_2026-09-03.zip")


def test_a_changed_publication_scheme_raises_rather_than_guessing() -> None:
    """A corpus built from a URL nobody verified is exactly what this replaced."""
    with pytest.raises(ValueError, match="scheme has changed"):
        resolve_latest_url("<html>nothing useful here</html>")


def test_only_english_topics_with_real_content_are_kept() -> None:
    """Spanish is in the same file, and stubs are pointers rather than information."""
    docs, total = parse_topics(_SAMPLE)

    assert total == 3
    assert [d.title for d in docs] == ["Fever"]
    assert all(len(d.text) > MIN_SUMMARY_CHARS for d in docs)


def test_markup_is_stripped_and_the_source_is_named_in_the_passage() -> None:
    """A retrieved passage carrying raw HTML is a passage a person cannot read.

    The attribution travels inside the text because the licence is attribution-only and a
    passage can be quoted anywhere, including into the doctor handover.
    """
    docs, _ = parse_topics(_SAMPLE)
    text = docs[0].text

    assert "<b>" not in text
    assert "&lt;" not in text
    assert "body temperature" in text
    assert "Also called: Pyrexia" in text
    assert "MedlinePlus" in text
    assert "not advice about any particular person" in text


def test_topics_are_layer_one_and_carry_their_licence() -> None:
    """Layer matters: it is how an interface can tell our own rules from fetched text."""
    docs, _ = parse_topics(_SAMPLE)

    assert docs[0].layer == 1
    assert docs[0].licence == "Attribution"
    assert docs[0].source_url.startswith("https://medlineplus.gov/")
    assert "National Library of Medicine" in docs[0].metadata["attribution"]


@pytest.mark.skipif(
    not Path("data/corpus/medlineplus/topics.xml").exists(),
    reason="no MedlinePlus release fetched in this checkout",
)
def test_the_authored_safety_rules_are_not_swamped_by_a_thousand_topics() -> None:
    """Adding MedlinePlus took the corpus from 133 chunks to about 1,850.

    The system's own escalation rules must stay findable, or someone asking about something
    urgent is shown a general article where the rule that applies to them should be. The
    deterministic floor does not depend on retrieval, so this is about what the person sees
    and what the model reasons over, not about whether an escalation fires.
    """
    from wha.retrieve.knowledge_docs import build_index

    index = build_index()

    for query, expected in (
        ("chest pain", "escalation_rf_chest_pain"),
        ("I fainted", "escalation_rf_syncope"),
        ("my chest hurts and I feel sick", "escalation_rf_chest_pain"),
    ):
        hits = index.query(query, top_k=6)
        assert any(h.chunk_id.startswith(expected) for h in hits), (
            f"'{query}' no longer surfaces {expected} in the top 6: {[h.chunk_id for h in hits]}"
        )


@pytest.mark.skipif(
    not Path("data/knowledge/corpus-sources.json").exists(),
    reason="no MedlinePlus release fetched in this checkout",
)
def test_the_snapshot_in_use_is_recorded_with_a_checksum() -> None:
    """A citation has to trace to a specific release, not to whatever the site served."""
    import json

    manifest = json.loads(Path("data/knowledge/corpus-sources.json").read_text(encoding="utf-8"))
    entry = manifest["medlineplus"]

    assert len(entry["sha256"]) == 64
    assert entry["snapshot_date"]
    assert entry["topics_kept"] > 0
    assert "attribution" in entry
