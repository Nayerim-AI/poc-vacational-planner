import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WikiDoc:
    id: str
    title: str
    url: str
    text: str


DESTINATION_KEYWORDS: Dict[str, List[str]] = {
    "Bali": ["bali", "ubud", "kuta", "denpasar", "nusa penida", "seminyak"],
    "Lisbon": ["lisbon", "alfama", "belém", "belem", "sintra"],
    "Tokyo": ["tokyo", "shinjuku", "shibuya", "asakusa", "ueno"],
}

BALI_POSITIVE = [
    "bali, indonesia",
    "island of bali",
    "on the island of bali",
    "karangasem",
    "karangasem regency",
    "denpasar",
    "ubud",
    "kuta",
    "seminyak",
    "nusa penida",
    "east bali",
    "north bali",
    "south bali",
]

BALI_NEGATIVE = [
    "crete",
    "greece",
    "new taipei",
    "taiwan",
    "bulacan",
    "philippines",
    "astrakhan",
    "russia",
]

LISBON_POSITIVE = [
    "lisbon, portugal",
    "capital of portugal",
    "portuguese capital",
    "tagus river",
    "bairro alto",
    "baixa",
    "alfama",
    "belém",
    "belem",
    "praça do comércio",
]

LISBON_NEGATIVE = [
    "maine",
    "new hampshire",
    "iowa",
    "ohio",
    "north dakota",
    "united states",
    "usa",
    "u.s.",
]

TOKYO_POSITIVE = [
    "tokyo, japan",
    "capital of japan",
    "japanese capital",
    "kantō region",
    "kanto region",
    "shinjuku",
    "shibuya",
    "asakusa",
    "ueno",
    "akihabara",
]

TOKYO_NEGATIVE = [
    "little tokyo",
    "los angeles",
    "california",
    "usa",
    "united states",
]


def iter_wiki_docs(base_path: Path) -> Iterator[WikiDoc]:
    """
    Scan wiki_00..wiki_99 files under base_path and yield WikiDoc objects for each <doc>.
    """
    for path in sorted(base_path.glob("wiki_*")):
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            in_doc = False
            doc_id = url = title = ""
            lines: List[str] = []
            for line in f:
                if line.startswith("<doc "):
                    in_doc = True
                    doc_id = _attr(line, "id")
                    url = _attr(line, "url")
                    title = _attr(line, "title")
                    lines = []
                    continue
                if line.startswith("</doc>") and in_doc:
                    text = "".join(lines).strip()
                    yield WikiDoc(id=doc_id, title=title, url=url, text=text)
                    in_doc = False
                    doc_id = url = title = ""
                    lines = []
                    continue
                if in_doc:
                    lines.append(line)


def _attr(tag_line: str, attr: str) -> str:
    match = re.search(fr'{attr}="([^"]*)"', tag_line)
    return match.group(1) if match else ""


def detect_destination(doc: WikiDoc) -> Optional[str]:
    """
    Return the destination name ("Bali", "Lisbon", "Tokyo") if the doc clearly belongs
    to one of them based on keyword matching in title and text. Otherwise return None.
    """
    haystack = f"{doc.title}\n{doc.text[:1500]}".lower()
    title_lower = doc.title.lower()

    def check_destination(name: str, base_keyword: str, positives: List[str], negatives: List[str]) -> Optional[tuple[str, int]]:
        if base_keyword not in haystack:
            return None
        if any(neg in haystack for neg in negatives):
            return None
        title_positive = any(pos in title_lower for pos in positives)
        text_positive = any(pos in haystack for pos in positives)
        if title_positive:
            return (name, 3)
        if text_positive:
            return (name, 2)
        keywords = DESTINATION_KEYWORDS.get(name, [])
        if any(kw in title_lower for kw in keywords):
            return (name, 2)
        if any(kw in haystack for kw in keywords):
            return (name, 1)
        return None

    candidates: List[tuple[str, int]] = []
    cand = check_destination("Bali", "bali", BALI_POSITIVE, BALI_NEGATIVE)
    if cand:
        candidates.append(cand)
    cand = check_destination("Lisbon", "lisbon", LISBON_POSITIVE, LISBON_NEGATIVE)
    if cand:
        candidates.append(cand)
    cand = check_destination("Tokyo", "tokyo", TOKYO_POSITIVE, TOKYO_NEGATIVE)
    if cand:
        candidates.append(cand)

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def extract_candidate_activities(doc: WikiDoc) -> List[str]:
    """
    From the doc.text, derive candidate 'Title | Short snippet' lines.
    Uses doc.title and the first non-empty paragraph as snippet.
    """
    paragraphs = [p.strip() for p in doc.text.split("\n\n") if p.strip()]
    snippet = ""
    for para in paragraphs:
        if len(para) >= 40:
            snippet = para.replace("\n", " ").strip()
            break
    if not snippet and paragraphs:
        snippet = paragraphs[0].replace("\n", " ").strip()
    if not snippet:
        return []
    if len(snippet) > 200:
        snippet = snippet[:197].rstrip() + "..."
    title = doc.title.strip() or "Activity"
    return [f"{title} | {snippet}"]


def build_wiki_activity_candidates(base_path: Path, output_dir: Path) -> None:
    """
    Scan all wiki files under base_path, detect destination, extract candidates,
    and write one file per destination: wiki_activities_<destination>.txt.
    Each line in the file is 'Title | Short snippet'.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    buckets: Dict[str, List[str]] = {"Bali": [], "Lisbon": [], "Tokyo": []}
    total_docs = 0
    matched_docs = 0
    for doc in iter_wiki_docs(base_path):
        total_docs += 1
        dest = detect_destination(doc)
        if not dest:
            continue
        matched_docs += 1
        candidates = extract_candidate_activities(doc)
        if candidates:
            buckets.setdefault(dest, []).extend(candidates)
    for dest, lines in buckets.items():
        out_path = output_dir / f"wiki_activities_{dest.lower()}.txt"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Wrote %d candidates for %s to %s", len(lines), dest, out_path)
    logger.info("Parsed %d docs, matched %d docs", total_docs, matched_docs)
