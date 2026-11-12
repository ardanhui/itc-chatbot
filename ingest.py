#!/usr/bin/env python3
"""Ingest the 7 PlacidWay source pages for the Website Knowledge Chatbot
assessment (AI Automation Assessment, Oct 7 2026).

Compliant fetch: respects robots.txt (User-agent * Allow: /, Crawl-delay 3),
identifies with a clear User-Agent, ~1 request per 3 seconds.
Extraction: visible text inside <main> (nav/header/footer stripped).
Headings (h2/h3) anchor the sections; body text is chunked at ~400 words.
The videos page is sourced from its JSON-LD VideoObjects (titles +
descriptions) instead of the card grid. JSON-LD facts (priceRange,
telephone, address) become one facts chunk per page when present.

Usage:
    python3 ingest.py            # fetch all 7 pages, write kb.json
    python3 ingest.py --use-cache  # reuse raw/*.html, only re-extract
Output:
    raw/<slug>.html              # raw HTML per page
    kb.json                      # {meta, sources, chunks[]}
"""
import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
RAW.mkdir(exist_ok=True)

UA = "PlacidWay-Chatbot-Assessment/1.0 (AI Automation Assessment research bot; respects robots.txt, 1 req/3s)"
CRAWL_DELAY = 3.0

SOURCES = [
    {"id": "profile", "type": "Clinic profile",
     "url": "https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center"},
    {"id": "package-adenocarcinoma", "type": "Treatment package",
     "url": "https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC"},
    {"id": "package-adrenal", "type": "Treatment package",
     "url": "https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC"},
    {"id": "package-anal", "type": "Treatment package",
     "url": "https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC"},
    {"id": "videos", "type": "Clinic videos",
     "url": "https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center"},
    {"id": "price-list", "type": "Price list",
     "url": "https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center"},
    {"id": "price-comparison", "type": "Price comparison",
     "url": "https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1"},
]

BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "li", "tr", "div", "section", "article"}
HEADING_TAGS = {"h2", "h3"}
# NOTE: "form" is deliberately NOT skipped — PlacidWay wraps page content in
# a <form>; only non-void chrome tags are skipped.
SKIP_TAGS = {"script", "style", "noscript", "svg", "select", "textarea", "button"}


class MainTextParser(HTMLParser):
    """Collect (heading, text) sections from inside <main>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main = 0
        self.skip_depth = 0  # plain counter: +1 on any SKIP start, -1 on any SKIP end
        self.in_heading = None
        self.heading_buf = []
        self.current_heading = ""
        self.sections = []  # list of [heading, [lines]]
        self.cur_lines = []

    def _flush(self):
        if self.cur_lines:
            self.sections.append((self.current_heading, list(self.cur_lines)))
            self.cur_lines = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.in_main += 1
            return
        if self.in_main == 0:
            return
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if tag in HEADING_TAGS:
            self._flush()
            self.in_heading = tag
            self.heading_buf = []
        elif tag in ("td", "th"):
            self.cur_lines.append(" | ")
        elif tag in BLOCK_TAGS:
            self.cur_lines.append("\n")

    def handle_endtag(self, tag):
        if tag == "main" and self.in_main > 0:
            self.in_main -= 1
            return
        if tag in SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if self.in_main == 0:
            return
        if tag == self.in_heading:
            self.current_heading = re.sub(r"\s+", " ", "".join(self.heading_buf)).strip()
            self.in_heading = None
            self.heading_buf = []
        elif tag in BLOCK_TAGS:
            self.cur_lines.append("\n")

    def handle_data(self, data):
        if self.in_main == 0 or self.skip_depth > 0:
            return
        text = data.strip()
        if not text:
            return
        if self.in_heading:
            self.heading_buf.append(text + " ")
        else:
            self.cur_lines.append(text + " ")


def clean_sections(raw_html: str) -> tuple[str, list]:
    title_m = re.search(r"<title>(.*?)</title>", raw_html, re.S | re.I)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
    parser = MainTextParser()
    parser.feed(raw_html)
    parser._flush()
    cleaned = []
    for heading, lines in parser.sections:
        text = "".join(lines)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        lines2 = [ln.strip() for ln in text.split("\n")]
        lines2 = [ln for ln in lines2 if len(ln) > 1]
        if lines2:
            cleaned.append((heading, "\n".join(lines2)))
    return title, cleaned


def chunk_sections(title: str, sections: list, source: dict, max_words: int = 400) -> list[dict]:
    chunks = []
    for heading, body in sections:
        words = body.split()
        if not words:
            continue
        for i in range(0, len(words), max_words):
            chunks.append({
                "source_id": source["id"],
                "source_type": source["type"],
                "source_url": source["url"],
                "page_title": title,
                "section": heading,
                "text": " ".join(words[i:i + max_words]),
            })
    return chunks


def json_ld_facts(raw_html: str) -> list[str]:
    """Pull simple facts (priceRange, telephone, address) from JSON-LD blocks,
    walking nested dicts/lists (e.g. ProfilePage.mainEntity.MedicalClinic).
    A facts entry is only kept when it carries a price, phone or address —
    bare names add nothing for retrieval."""
    found = {"name": set(), "priceRange": set(), "telephone": set(), "address": set()}

    def has_digits(s):
        return any(ch.isdigit() for ch in str(s))

    ORG_TYPES = {"MedicalClinic", "MedicalOrganization", "Hospital", "LocalBusiness",
                "Organization", "MedicalBusiness", "HealthAndBeautyBusiness"}

    def walk(node):
        if isinstance(node, dict):
            name = node.get("name") or ""
            # names only from clinic/org entities, or from the node that also
            # carries price/phone/address (FAQ/video/testimonial names excluded)
            has_contact = any(
                (node.get(k) and has_digits(node[k])) for k in ("priceRange", "telephone")
            ) or isinstance(node.get("address"), dict)
            if name and (node.get("@type") in ORG_TYPES or has_contact):
                found["name"].add(str(name).strip())
            if node.get("priceRange") and has_digits(node["priceRange"]):
                found["priceRange"].add(str(node["priceRange"]).strip())
            if node.get("telephone") and has_digits(node["telephone"]):
                found["telephone"].add(str(node["telephone"]).strip())
            addr = node.get("address")
            if isinstance(addr, dict):
                a = ", ".join(str(v) for v in addr.values() if isinstance(v, str) and v.strip())
                if a:
                    found["address"].add(a)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', raw_html, re.S | re.I
    ):
        try:
            walk(json.loads(m.group(1)))
        except Exception:
            continue
    bits = []
    if found["name"]:
        bits.append("Name: " + "; ".join(sorted(found["name"])))
    if found["priceRange"]:
        bits.append("Price range: " + "; ".join(sorted(found["priceRange"])))
    if found["telephone"]:
        bits.append("Telephone: " + "; ".join(sorted(found["telephone"])))
    if found["address"]:
        bits.append("Address: " + "; ".join(sorted(found["address"])))
    # only emit when a price, phone or address was actually found
    if not (found["priceRange"] or found["telephone"] or found["address"]):
        return []
    return ["; ".join(bits)] if bits else []


def video_chunks(raw_html: str, title: str, source: dict) -> list[dict]:
    """Build chunks from JSON-LD VideoObjects (name + description + url)."""
    videos = []
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', raw_html, re.S | re.I
    ):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and it.get("@type") == "VideoObject" and it.get("name"):
                videos.append(it)
    seen, uniq = set(), []
    for v in videos:
        key = v["name"].strip().lower()
        if key not in seen:
            seen.add(key)
            uniq.append(v)
    chunks = []
    group, groups = [], []
    for v in uniq:
        entry = f"Video: {v['name'].strip()}"
        if v.get("description"):
            entry += f" — {re.sub(chr(92) + 's+', ' ', str(v['description'])).strip()}"
        if v.get("contentUrl"):
            entry += f" ({v['contentUrl']})"
        group.append(entry)
        if len(group) >= 10:
            groups.append(group)
            group = []
    if group:
        groups.append(group)
    for g in groups:
        chunks.append({
            "source_id": source["id"],
            "source_type": source["type"],
            "source_url": source["url"],
            "page_title": title,
            "section": "Clinic videos",
            "text": "\n".join(g),
        })
    return chunks, len(uniq)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main():
    use_cache = "--use-cache" in sys.argv
    # UI chrome that leaked into <main>: the embedded chat widget and the
    # search-form labels. They carry no facts and confuse retrieval.
    JUNK_MARKERS = ["PlacidWay Virtual Assistant", "Save conversation",
                    "Privacy & security", "What treatment? Any Procedure"]
    all_chunks = []
    sources_meta = []
    for i, src in enumerate(SOURCES):
        if i > 0 and not use_cache:
            time.sleep(CRAWL_DELAY)
        print(f"[{i+1}/7] {src['id']} ...", flush=True)
        path = RAW / f"{src['id']}.html"
        if use_cache and path.exists():
            html = path.read_bytes()
        else:
            html = fetch(src["url"])
            path.write_bytes(html)
        text = html.decode("utf-8", "replace")
        title, sections = clean_sections(text)
        if src["id"] == "videos":
            chunks, n_videos = video_chunks(text, title, src)
            n_chars = sum(len(c["text"]) for c in chunks)
            print(f"    title: {title[:80]}")
            print(f"    videos: {n_videos}, chunks: {len(chunks)}")
        else:
            chunks = chunk_sections(title, sections, src)
            facts = json_ld_facts(text)
            if facts:
                chunks.insert(0, {
                    "source_id": src["id"], "source_type": src["type"],
                    "source_url": src["url"], "page_title": title,
                    "section": "Key facts (structured data)",
                    "text": "\n".join(facts),
                })
            n_chars = sum(len(c["text"]) for c in chunks)
            prices = sorted(set(re.findall(r"\$[\d,]+(?:\.\d+)?", " ".join(c["text"] for c in chunks))))
            print(f"    title: {title[:80]}")
            print(f"    sections: {len(sections)}, chars: {n_chars}, chunks: {len(chunks)}, prices: {prices[:12]}")
        chunks = [c for c in chunks if not any(m in c["text"] for m in JUNK_MARKERS)]
        sources_meta.append({**src, "title": title, "chunks": len(chunks)})
        all_chunks.extend(chunks)
    kb = {
        "meta": {
            "name": "PlacidWay ITC chatbot knowledge base",
            "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_count": len(SOURCES),
            "chunk_count": len(all_chunks),
            "chunk_max_words": 400,
            "crawl": "robots.txt Allow: / for User-agent *, Crawl-delay 3, 1 req/3s, UA PlacidWay-Chatbot-Assessment/1.0",
        },
        "sources": sources_meta,
        "chunks": all_chunks,
    }
    (BASE / "kb.json").write_text(json.dumps(kb, indent=1, ensure_ascii=False), encoding="utf-8")
    total_chars = sum(len(c["text"]) for c in all_chunks)
    print(f"\nDONE: {len(all_chunks)} chunks, {total_chars} chars from 7 pages -> kb.json")


if __name__ == "__main__":
    main()
