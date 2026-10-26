#!/usr/bin/env python3
"""Re-runnable measurements for a fetched pre-2022 arXiv abstract corpus."""
from __future__ import annotations
import argparse, json, math, re
from collections import Counter
from datetime import datetime
from pathlib import Path

WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
NUMBER_RE = re.compile(r"(?<!\w)(?:\d+(?:[.,]\d+)*(?:%|[eE][+-]?\d+)?)")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\\])")
TRANSITIONS = {
    "furthermore": r"\bfurthermore\b",
    "moreover": r"\bmoreover\b",
    "additionally": r"\badditionally\b",
    "however": r"\bhowever\b",
    "therefore": r"\btherefore\b",
    "finally": r"\bfinally\b",
    "in conclusion": r"\bin conclusion\b",
    "in summary": r"\bin summary\b",
    "in this paper": r"\bin this paper\b",
    "in this work": r"\bin this work\b",
    "we propose": r"\bwe propose\b",
    "we show": r"\bwe show\b",
    "we find": r"\bwe find\b",
}
METHOD_DATASET_RE = re.compile(
    r"\b(?:dataset|data set|corpus|benchmark|algorithm|method|approach|framework|model|"
    r"architecture|network|classifier|regression|transformer|simulation|experiment|"
    r"training set|test set|evaluation set)\b", re.I
)
SUBORDINATE_MARKERS = [
    "although", "because", "if", "since", "unless", "when", "while", "whereas",
    "which", "who", "that", "as", "before", "after", "once", "though", "whether",
]
SUBORDINATE_RE = re.compile(r"\b(" + "|".join(SUBORDINATE_MARKERS) + r")\b", re.I)


def sentences(text: str) -> list[str]:
    # Deliberately conservative, deterministic segmentation; measurements are corpus-level.
    return [s.strip() for s in SENTENCE_RE.split(text.strip()) if s.strip()]


def sentence_words(s: str) -> int:
    return len(WORD_RE.findall(s))


def clause_position(s: str) -> str | None:
    markers = list(SUBORDINATE_RE.finditer(s))
    if not markers:
        return None
    # Ignore a marker in the first three characters only when it is not clause-like.
    m = markers[0]
    prefix_words = sentence_words(s[:m.start()])
    suffix_words = sentence_words(s[m.end():])
    if prefix_words <= 2:
        return "start"
    if suffix_words <= 5:
        return "end"
    return "middle"


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mu = mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    data = json.loads(args.corpus.read_text(encoding="utf-8"))
    papers = data["papers"]
    all_sentences: list[str] = []
    lengths: list[int] = []
    sequence_counts: Counter[tuple[int, ...]] = Counter()
    total_words = 0
    total_numbers = 0
    transition_counts = Counter()
    papers_with_numbers = 0
    papers_with_method_dataset = 0
    starts_in_this_paper_work = 0
    clause_counts = Counter()

    for paper in papers:
        abstract = paper["abstract"]
        ws = WORD_RE.findall(abstract)
        total_words += len(ws)
        nums = NUMBER_RE.findall(abstract)
        total_numbers += len(nums)
        papers_with_numbers += bool(nums)
        papers_with_method_dataset += bool(METHOD_DATASET_RE.search(abstract))
        first = sentences(abstract)
        if first and re.match(r"^in this (?:paper|work)\b", first[0], re.I):
            starts_in_this_paper_work += 1
        seq = tuple(sentence_words(s) for s in first)
        if seq:
            sequence_counts[seq] += 1
        for s in first:
            all_sentences.append(s)
            lengths.append(sentence_words(s))
            pos = clause_position(s)
            if pos:
                clause_counts[pos] += 1
        lower = abstract.lower()
        for label, pattern in TRANSITIONS.items():
            transition_counts[label] += len(re.findall(pattern, lower))

    sample = all_sentences[:100]
    sample_clause_counts = Counter(clause_position(s) for s in sample if clause_position(s))
    mu = mean(lengths)
    sigma = sd(lengths)
    results = {
        "source_corpus": str(args.corpus),
        "field": data.get("field"),
        "paper_count": len(papers),
        "date_filter": data.get("date_filter"),
        "sentence_count": len(lengths),
        "word_count": total_words,
        "sentence_length_words": {
            "mean": round(mu, 4),
            "sample_sd": round(sigma, 4),
            "cv": round(sigma / mu, 4) if mu else 0.0,
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "pct_le_10": round(100 * sum(x <= 10 for x in lengths) / len(lengths), 4) if lengths else 0.0,
            "pct_ge_30": round(100 * sum(x >= 30 for x in lengths) / len(lengths), 4) if lengths else 0.0,
        },
        "common_sentence_length_sequences_per_abstract": [
            {"sequence": list(seq), "abstracts": n} for seq, n in sequence_counts.most_common(10)
        ],
        "transition_rates_per_1000_words": {
            label: {"count": transition_counts[label], "rate": round(1000 * transition_counts[label] / total_words, 4)}
            for label in TRANSITIONS
        },
        "specificity": {
            "numbers_total": total_numbers,
            "numbers_per_1000_words": round(1000 * total_numbers / total_words, 4) if total_words else 0.0,
            "pct_papers_with_at_least_one_number": round(100 * papers_with_numbers / len(papers), 4) if papers else 0.0,
            "pct_papers_naming_dataset_or_method": round(100 * papers_with_method_dataset / len(papers), 4) if papers else 0.0,
            "pct_abstracts_starting_in_this_paper_or_work": round(100 * starts_in_this_paper_work / len(papers), 4) if papers else 0.0,
            "dataset_method_indicator_regex": METHOD_DATASET_RE.pattern,
        },
        "clause_positions": {
            "sample_size_sentences": len(sample),
            "method": "Deterministic marker rules using subordinating conjunction/relative-clause markers; sample is first 100 segmented sentences, with marker taxonomy recorded for audit.",
            "counts": dict(sample_clause_counts),
            "percent_of_marked_sample": {
                k: round(100 * v / sum(sample_clause_counts.values()), 4) for k, v in sample_clause_counts.items()
            } if sample_clause_counts else {},
            "markers": SUBORDINATE_MARKERS,
        },
    }
    args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(json.dumps(results["sentence_length_words"], indent=2))

if __name__ == "__main__":
    main()
