#!/usr/bin/env python3
"""Local run utility reconstructed because the named repository script is absent."""
from __future__ import annotations
import argparse, json, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
CUTOFF = datetime(2022, 12, 1, tzinfo=timezone.utc)


def fetch(category: str, count: int, out: Path) -> None:
    records = []
    start = 0
    page_size = min(200, count)
    while len(records) < count:
        query = f"cat:{category} AND submittedDate:[201501010000 TO 202211300000]"
        params = urlencode({"search_query": query, "start": start, "max_results": page_size})
        url = "https://export.arxiv.org/api/query?" + params
        req = Request(url, headers={"User-Agent": "CanopusHumanizerCorpusResearch/1.0"})
        with urlopen(req, timeout=60) as response:
            payload = response.read()
        root = ET.fromstring(payload)
        entries = root.findall("atom:entry", NS)
        if not entries:
            break
        for entry in entries:
            ident = (entry.findtext("atom:id", default="", namespaces=NS)).strip()
            title = " ".join((entry.findtext("atom:title", default="", namespaces=NS)).split())
            abstract = " ".join((entry.findtext("atom:summary", default="", namespaces=NS)).split())
            published = (entry.findtext("atom:published", default="", namespaces=NS)).strip()
            if not ident or not title or not abstract or not published:
                continue
            date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if date < datetime(2015, 1, 1, tzinfo=timezone.utc) or date >= CUTOFF:
                continue
            records.append({
                "arxiv_id": ident.rsplit("/", 1)[-1],
                "title": title,
                "submitted_date": published,
                "abstract": abstract,
            })
            if len(records) >= count:
                break
        start += len(entries)
        if len(entries) < page_size:
            break
        if len(records) < count:
            time.sleep(3.2)
    if len(records) < count:
        raise RuntimeError(f"Only collected {len(records)} complete records; required {count}")
    out.write_text(json.dumps({
        "field": category,
        "date_filter": "2015-01-01 through 2022-11-30",
        "source": "https://export.arxiv.org/api/query",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "papers": records,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(records)} papers)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True)
    parser.add_argument("--max-results", type=int, default=500)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    fetch(args.category, args.max_results, args.out)
