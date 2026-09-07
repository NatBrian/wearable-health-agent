"""Fetching and parsing MedlinePlus health topics, the consumer-language corpus layer.

Until this existed the agent could cite why a night was flagged, what else might explain
it, and the rule behind an escalation, but nothing at all about a condition. Asked what a
fever means it had to refuse, because the only alternative was to write clinical text from
the model's own knowledge, which this build must not do.

MedlinePlus is the National Library of Medicine's consumer health information. It is free,
requires no registration, and is attribution-only, which is why `sources.yaml` chose it
over every other candidate.

**The URL recorded in sources.yaml was dead.** It named
``mplus_topics_compressed.zip``, and no such undated file exists or appears ever to have
existed: MedlinePlus publishes dated snapshots, Tuesday to Saturday, as
``mplus_topics_compressed_YYYY-MM-DD.zip``. This module resolves the newest one from the
index page at fetch time rather than hardcoding anything, which also means the exact
snapshot in use is a recorded fact rather than an assumption.

Everything fetched here is **untrusted text from outside the repository**. It is scanned
for injection before the model sees it, in ``tool_retrieve_clinical_evidence``, on the same
footing as any other retrieved passage.
"""

import hashlib
import io
import re
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from wha.clock import now_utc
from wha.retrieve.models import CorpusDocument

INDEX_URL = "https://medlineplus.gov/xml.html"
COMPRESSED_PATTERN = re.compile(
    r"https://medlineplus\.gov/xml/mplus_topics_compressed_(\d{4}-\d{2}-\d{2})\.zip"
)
CORPUS_DIR = Path("data/corpus/medlineplus")
ATTRIBUTION = (
    "MedlinePlus, National Library of Medicine, National Institutes of Health. "
    "Free to use with attribution."
)

# A topic summary shorter than this is a stub or a pointer rather than health information,
# and indexing it adds a retrievable passage that can only ever waste a citation slot.
MIN_SUMMARY_CHARS = 200


@dataclass
class Snapshot:
    """Which MedlinePlus release is in use, and proof of what was in it."""

    snapshot_date: str
    url: str
    sha256: str
    fetched_at_utc: str
    topics_total: int
    topics_kept: int
    bytes_downloaded: int


def resolve_latest_url(index_html: str) -> tuple[str, str]:
    """The newest dated compressed topics file named on the index page.

    Raises rather than falling back to a guess. A corpus built from a URL nobody verified
    is exactly the situation this function exists to end.
    """
    matches = COMPRESSED_PATTERN.findall(index_html)
    if not matches:
        raise ValueError(
            "No dated MedlinePlus topics archive found on the index page. The publication "
            "scheme has changed again and this needs a human to look at it."
        )
    latest = max(matches)
    return (
        f"https://medlineplus.gov/xml/mplus_topics_compressed_{latest}.zip",
        latest,
    )


def _strip_markup(raw: str) -> str:
    """Summaries are HTML fragments. Keep the sentences, drop the tags and entities."""
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )
    return " ".join(text.split())


def parse_topics(xml_bytes: bytes, language: str = "English") -> tuple[list[CorpusDocument], int]:
    """Turn the release into citable documents, one per health topic.

    Returns the documents and the total number of topics seen, so the caller can record how
    much was kept and why. Only ``language`` is kept: the file carries English and Spanish
    together, and indexing both halves for a person reading English adds a thousand
    passages that can never be the right answer.
    """
    root = ElementTree.fromstring(xml_bytes)
    docs: list[CorpusDocument] = []
    total = 0

    for topic in root.iter("health-topic"):
        total += 1
        if topic.get("language") != language:
            continue

        title = (topic.get("title") or "").strip()
        url = (topic.get("url") or "").strip()
        summary = _strip_markup(topic.findtext("full-summary") or "")
        if not title or len(summary) < MIN_SUMMARY_CHARS:
            continue

        also_called = [e.text.strip() for e in topic.findall("also-called") if e.text]
        groups = [e.text.strip() for e in topic.findall("group") if e.text]
        mesh = [
            d.text.strip()
            for e in topic.findall("mesh-heading")
            for d in e.findall("descriptor")
            if d.text
        ]

        lines = [f"# {title}", ""]
        if also_called:
            lines += [f"Also called: {', '.join(also_called)}.", ""]
        lines += [summary, ""]
        if groups:
            lines += [f"Topic group: {', '.join(groups)}.", ""]
        lines += [
            (
                "Source: MedlinePlus, National Library of Medicine. This is general health "
                "information, not advice about any particular person, and it says nothing "
                "about this person's own readings."
            ),
        ]

        docs.append(
            CorpusDocument(
                doc_id=f"medlineplus_{topic.get('id') or re.sub(r'\\W+', '_', title.lower())}",
                title=title,
                layer=1,
                source_url=url,
                licence="Attribution",
                text="\n".join(lines),
                metadata={
                    "topic": "consumer_health",
                    "also_called": also_called,
                    "groups": groups,
                    "mesh": mesh,
                    "attribution": ATTRIBUTION,
                },
            )
        )

    return docs, total


def fetch(target_dir: Path | None = None, timeout: float = 120.0) -> Snapshot:
    """Download the newest release and store the raw XML, unmodified, on disk.

    The raw file is kept rather than only the parsed output, so the parse can be re-run and
    checked later without another download, and so the checksum recorded in the manifest
    refers to something that still exists.
    """
    destination = target_dir or CORPUS_DIR
    destination.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(INDEX_URL, headers={"User-Agent": "WHA/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        index_html = response.read().decode("utf-8", errors="replace")

    url, snapshot_date = resolve_latest_url(index_html)

    request = urllib.request.Request(url, headers={"User-Agent": "WHA/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()

    digest = hashlib.sha256(payload).hexdigest()

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".xml"))
        xml_bytes = archive.read(name)

    (destination / "topics.xml").write_bytes(xml_bytes)
    docs, total = parse_topics(xml_bytes)

    return Snapshot(
        snapshot_date=snapshot_date,
        url=url,
        sha256=digest,
        fetched_at_utc=now_utc().isoformat(),
        topics_total=total,
        topics_kept=len(docs),
        bytes_downloaded=len(payload),
    )


def load_local(target_dir: Path | None = None) -> list[CorpusDocument]:
    """The parsed topics, if a release has been fetched. Empty when it has not.

    Empty is the correct behaviour rather than an error: the rest of the corpus is authored
    in this repository and works without this layer. Its absence is disclosed to the person
    rather than crashing the agent.
    """
    source = (target_dir or CORPUS_DIR) / "topics.xml"
    if not source.exists():
        return []
    docs, _ = parse_topics(source.read_bytes())
    return docs
