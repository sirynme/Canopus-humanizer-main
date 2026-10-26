"""Descriptive linguistic metrics, entropy, compression ratio, and readability formulas."""

import collections
import math
import re
import zlib
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class TextMetricsResult:
    """Container for transparent descriptive text measurements."""
    character_count: int
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_sentence_length: float
    sentence_length_std_dev: float
    type_token_ratio: float
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    zlib_compression_ratio: float
    shannon_entropy: float
    disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_count": self.character_count,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "paragraph_count": self.paragraph_count,
            "avg_sentence_length": round(self.avg_sentence_length, 2),
            "sentence_length_std_dev": round(self.sentence_length_std_dev, 2),
            "type_token_ratio": round(self.type_token_ratio, 4),
            "flesch_reading_ease": round(self.flesch_reading_ease, 2),
            "flesch_kincaid_grade": round(self.flesch_kincaid_grade, 2),
            "zlib_compression_ratio": round(self.zlib_compression_ratio, 4),
            "shannon_entropy": round(self.shannon_entropy, 4),
            "disclaimer": self.disclaimer,
        }


class TextMetricsCalculator:
    """
    Computes rigorous descriptive text measurements.
    Strictly documents that compression, entropy, and readability metrics
    do NOT constitute proof of authorship, AI generation, or academic misconduct.
    """

    METRICS_DISCLAIMER = (
        "Notice: Text statistics, compression ratio, Shannon entropy, and readability scores "
        "measure surface information density and token distribution. They do not reliably "
        "establish authorship, intent, or AI-generated status."
    )

    @staticmethod
    def _count_syllables_in_word(word: str) -> int:
        """Heuristic syllable counter for English words (used in Flesch formulas)."""
        w = word.lower().strip()
        if len(w) <= 3:
            return 1
        # Remove trailing silent e
        w = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", w)
        syllables = len(re.findall(r"[aeiouy]{1,2}", w))
        return max(1, syllables)

    def calculate(self, text: str) -> TextMetricsResult:
        """Calculates full metrics battery on the input text."""
        if not text or not text.strip():
            return TextMetricsResult(
                character_count=len(text),
                word_count=0,
                sentence_count=0,
                paragraph_count=0,
                avg_sentence_length=0.0,
                sentence_length_std_dev=0.0,
                type_token_ratio=0.0,
                flesch_reading_ease=0.0,
                flesch_kincaid_grade=0.0,
                zlib_compression_ratio=0.0,
                shannon_entropy=0.0,
                disclaimer=self.METRICS_DISCLAIMER,
            )

        char_count = len(text)
        words = re.findall(r"\b[a-zA-Z0-9_\'-]+\b", text)
        word_count = len(words)
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        para_count = len(paragraphs)

        # Sentences split on terminal punctuation
        sentences = [s.strip() for s in re.split(r"[.!?]+(?:\s+|$)", text) if s.strip()]
        sentence_count = max(1, len(sentences))

        # Sentence length statistics
        sent_lens = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
        sent_lens = [sl for sl in sent_lens if sl > 0] or [word_count]
        avg_sent_len = sum(sent_lens) / len(sent_lens)

        if len(sent_lens) > 1:
            variance = sum((x - avg_sent_len) ** 2 for x in sent_lens) / (len(sent_lens) - 1)
            sent_len_std = math.sqrt(variance)
        else:
            sent_len_std = 0.0

        # Type-Token Ratio (vocabulary richness)
        lower_words = [w.lower() for w in words]
        unique_words = set(lower_words)
        ttr = len(unique_words) / max(1, word_count)

        # Flesch Readability Formulas
        total_syllables = sum(self._count_syllables_in_word(w) for w in words)
        words_per_sent = word_count / sentence_count
        syllables_per_word = total_syllables / max(1, word_count)

        # Flesch Reading Ease = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
        flesch_ease = 206.835 - (1.015 * words_per_sent) - (84.6 * syllables_per_word)
        # Flesch-Kincaid Grade Level = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
        flesch_grade = (0.39 * words_per_sent) + (11.8 * syllables_per_word) - 15.59

        # Zlib Compression Ratio: compressed bytes / uncompressed bytes
        encoded_bytes = text.encode("utf-8")
        if encoded_bytes:
            compressed = zlib.compress(encoded_bytes, level=6)
            compression_ratio = len(compressed) / len(encoded_bytes)
        else:
            compression_ratio = 1.0

        # Character Shannon Entropy: - sum(p_i * log2(p_i))
        if encoded_bytes:
            counts = collections.Counter(encoded_bytes)
            total = len(encoded_bytes)
            entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        else:
            entropy = 0.0

        return TextMetricsResult(
            character_count=char_count,
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=para_count,
            avg_sentence_length=avg_sent_len,
            sentence_length_std_dev=sent_len_std,
            type_token_ratio=ttr,
            flesch_reading_ease=flesch_ease,
            flesch_kincaid_grade=flesch_grade,
            zlib_compression_ratio=compression_ratio,
            shannon_entropy=entropy,
            disclaimer=self.METRICS_DISCLAIMER,
        )
