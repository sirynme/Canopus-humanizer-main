"""Stage 2: Document and content-type classification and editing needs analyzer."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple


@dataclass(frozen=True)
class DocumentClassification:
    """Classification metadata and identified editing needs for a document."""
    content_type: str  # "academic", "technical", "general_essay", "code_comment"
    confidence: float
    editing_needs: Tuple[str, ...]  # ("grammar", "redundancy", "awkward_phrasing", "transitions")
    is_already_clear: bool
    word_count: int
    sentence_count: int
    features: Dict[str, Any] = field(default_factory=dict)


ACADEMIC_INDICATORS = [
    r"\b(?:hypothesis|methodology|empirical|prior\s+investigations|literature\s+review)\b",
    r"\b(?:statistically\s+significant|confidence\s+interval|regression\s+analysis)\b",
    r"\b(?:findings|corroborate|postulate|subsequent\s+investigation)\b",
    r"\([A-Z][a-zA-Z\s&]+(?:et\s+al\.)?,\s*\d{4}\)",
    r"\[\d+(?:[,\-–]\s*\d+)*\]",
]

TECHNICAL_INDICATORS = [
    r"```[\s\S]*?```|`[^`\n]+`",
    r"\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]",
    r"(?<!\\)\$(?!\s|\d)(?:[^\$\n\\]|\\.)+?(?<!\s)\$",
    r"\b(?:algorithm|kernel|complexity|asymptotic|\bO\([n1\w\s\*\+\^]+\)|latency|throughput|API|RAM|CPU|GPU)\b",
    r"\b\d+(?:\.\d+)?\s*(?:ms|GB|MB|queries\s+per\s+second|ppm|GHz)\b",
]

AWKWARD_PATTERNS = [
    r"\bdelve\s+into\b",
    r"\bstands\s+as\s+a\s+testament\s+to\b",
    r"\bcomprehensive\s+tapestry\b",
    r"\bin\s+today's\s+digital\s+era\b",
    r"\bplays\s+a\s+crucial\s+role\s+in\b",
]

REDUNDANCY_PATTERNS = [
    r"\bdue\s+to\s+the\s+fact\s+that\b",
    r"\bin\s+order\s+to\b",
    r"\bfor\s+the\s+purpose\s+of\b",
    r"\bat\s+this\s+point\s+in\s+time\b",
    r"\ba\s+large\s+number\s+of\b",
    r"\bit\s+is\s+worth\s+noting\s+that\b",
    r"\bby\s+means\s+of\b",
    r"\bwith\s+respect\s+to\b",
    r"\bas\s+a\s+result\s+of\b",
    r"\bclose\s+proximity\b",
    r"\bcollaborate\s+together\b",
    r"\bconsensus\s+of\s+opinion\b",
    r"\bend\s+result\b",
    r"\bfuture\s+plans\b",
    r"\bpast\s+history\b",
]

GRAMMAR_PATTERNS = [
    r"\birregardless\b",
    r"\bcould\s+of\b",
    r"\bshould\s+of\b",
    r"\bwould\s+of\b",
    r"\bcomprise\s+of\b",
    r"\bdifferent\s+than\s+(?:the|this|that|a|an|[a-zA-Z]+)\b",
    r"\breason\s+(?:why\s+)?is\s+because\b",
    r"\b(?:criteria|phenomena)\s+is\b",
    r"\b(?:criterion|phenomenon)\s+are\b",
    r"\s+[,.!?;:]",  # Space before punctuation
    r"\b([a-zA-Z]+)\s+\1\b",  # Repeated word like "the the"
]


class DocumentClassifier:
    """Classifies document style and identifies specific editing needs."""

    def classify(self, text: str) -> DocumentClassification:
        if not text or not text.strip():
            return DocumentClassification(
                content_type="general_essay",
                confidence=1.0,
                editing_needs=(),
                is_already_clear=True,
                word_count=0,
                sentence_count=0,
                features={},
            )

        words = text.split()
        word_count = len(words)
        # Approximate sentence count
        sentence_count = max(1, len(re.findall(r"[.!?]+(?:\s+|$)", text)))

        # 1. Content Type Scoring
        academic_score = sum(len(re.findall(p, text, re.IGNORECASE)) for p in ACADEMIC_INDICATORS)
        technical_score = sum(len(re.findall(p, text, re.IGNORECASE)) for p in TECHNICAL_INDICATORS)

        is_code_comment = text.strip().startswith(("#", "//", "/*", "*"))
        if is_code_comment:
            content_type = "code_comment"
            confidence = 0.95
        elif technical_score > 2 and technical_score >= academic_score:
            content_type = "technical"
            confidence = min(0.95, 0.60 + technical_score * 0.08)
        elif academic_score > 1 or (academic_score > 0 and technical_score > 0):
            content_type = "academic"
            confidence = min(0.95, 0.60 + academic_score * 0.08)
        else:
            content_type = "general_essay"
            confidence = 0.75

        # 2. Identify Editing Needs
        editing_needs: List[str] = []

        grammar_matches = sum(len(re.findall(p, text, re.IGNORECASE)) for p in GRAMMAR_PATTERNS)
        if grammar_matches > 0:
            editing_needs.append("grammar")

        redundancy_matches = sum(len(re.findall(p, text, re.IGNORECASE)) for p in REDUNDANCY_PATTERNS)
        if redundancy_matches > 0:
            editing_needs.append("redundancy")

        awkward_matches = sum(len(re.findall(p, text, re.IGNORECASE)) for p in AWKWARD_PATTERNS)
        if awkward_matches > 0:
            editing_needs.append("awkward_phrasing")

        # Check transition and coherence
        has_transitions = bool(re.search(r"\b(?:However|Moreover|Furthermore|Therefore|Consequently|Thus|In summary),", text))
        if sentence_count >= 3 and not has_transitions:
            editing_needs.append("transitions")

        # 3. Already Clear Determination
        # A passage is already clear if it has no awkward tropes, no redundancies,
        # no grammar flaws, reasonable sentence lengths, and no known tell phrases.
        avg_sentence_len = word_count / max(1, sentence_count)
        is_already_clear = (
            grammar_matches == 0
            and redundancy_matches == 0
            and awkward_matches == 0
            and 8 <= avg_sentence_len <= 35
        )

        features = {
            "academic_score": academic_score,
            "technical_score": technical_score,
            "grammar_flaws_count": grammar_matches,
            "redundancy_count": redundancy_matches,
            "awkward_phrases_count": awkward_matches,
            "avg_sentence_length": round(avg_sentence_len, 1),
            "has_citations": bool(re.search(r"\[\d+\]|\([A-Z].*?\d{4}\)", text)),
        }

        return DocumentClassification(
            content_type=content_type,
            confidence=round(confidence, 2),
            editing_needs=tuple(editing_needs),
            is_already_clear=is_already_clear,
            word_count=word_count,
            sentence_count=sentence_count,
            features=features,
        )
