"""Text segmentation and source offset tracking."""

import re
from dataclasses import dataclass
from typing import List, Tuple


COMMON_ABBREVIATIONS = {
    "e.g.",
    "i.e.",
    "et al.",
    "al.",
    "p.m.",
    "a.m.",
    "dr.",
    "prof.",
    "fig.",
    "figs.",
    "vs.",
    "cf.",
    "approx.",
    "ref.",
    "no.",
    "vol.",
    "dept.",
    "univ.",
    "ed.",
    "eds.",
    "jan.",
    "feb.",
    "mar.",
    "apr.",
    "jun.",
    "jul.",
    "aug.",
    "sep.",
    "sept.",
    "oct.",
    "nov.",
    "dec.",
    "ph.d.",
    "m.s.",
    "b.s.",
    "inc.",
    "ltd.",
    "corp.",
    "eq.",
    "eqs.",
    "sec.",
    "secs.",
    "st.",
}


@dataclass(frozen=True)
class TextSegment:
    """Represents a segmented prose unit with exact character offsets in source text."""
    segment_id: str
    start: int
    end: int
    text: str
    block_type: str = "sentence"


class TextSegmenter:
    """Deterministic segmenter tracking stable source offsets for paragraphs and sentences."""

    def split_paragraphs(self, text: str) -> List[TextSegment]:
        """Splits text into paragraphs preserving blank line spacing and exact offsets."""
        segments: List[TextSegment] = []
        if not text:
            return segments

        # Split on double or more newlines
        para_pattern = re.compile(r"(\n\s*\n+)")
        last_end = 0
        idx = 0

        for match in para_pattern.finditer(text):
            p_start = last_end
            p_end = match.start()
            content = text[p_start:p_end]
            if content.strip():
                segments.append(
                    TextSegment(
                        segment_id=f"para_{idx:04d}",
                        start=p_start,
                        end=p_end,
                        text=content,
                        block_type="paragraph",
                    )
                )
                idx += 1
            last_end = match.end()

        # Final trailing paragraph
        if last_end < len(text):
            content = text[last_end:]
            if content.strip():
                segments.append(
                    TextSegment(
                        segment_id=f"para_{idx:04d}",
                        start=last_end,
                        end=len(text),
                        text=content,
                        block_type="paragraph",
                    )
                )

        return segments

    def split_sentences(self, paragraph_text: str, offset_base: int = 0) -> List[TextSegment]:
        """
        Segments a single paragraph into sentences with offsets.
        Safeguards abbreviations, decimals, initials, and citation markers.
        """
        if not paragraph_text:
            return []

        sentences: List[TextSegment] = []
        n = len(paragraph_text)
        start = 0
        idx = 0

        # Look for potential terminal punctuation: . ! ?
        punct_pattern = re.compile(r"([.!?])(?:\s+|$)")
        pos = 0

        while pos < n:
            m = punct_pattern.search(paragraph_text, pos)
            if not m:
                # Remainder of paragraph is final sentence
                tail = paragraph_text[start:].strip()
                if tail:
                    s_off = paragraph_text.find(tail, start)
                    sentences.append(
                        TextSegment(
                            segment_id=f"sent_{idx:04d}",
                            start=offset_base + s_off,
                            end=offset_base + s_off + len(tail),
                            text=tail,
                            block_type="sentence",
                        )
                    )
                break

            punct_idx = m.start(1)
            punct_char = paragraph_text[punct_idx]
            match_end = m.end()

            # Check if this period is part of an abbreviation, decimal, or initial
            is_abbrev = False
            if punct_char == ".":
                # Check for decimal number e.g. 3.14
                if punct_idx > 0 and punct_idx < n - 1:
                    if paragraph_text[punct_idx - 1].isdigit() and paragraph_text[punct_idx + 1].isdigit():
                        is_abbrev = True

                # Check for single initial e.g. "J. Smith"
                if not is_abbrev and punct_idx >= 1:
                    prev_word = paragraph_text[max(0, punct_idx - 2):punct_idx]
                    if len(prev_word) == 1 and prev_word.isupper():
                        is_abbrev = True
                    elif len(prev_word) == 2 and prev_word[0] == " " and prev_word[1].isupper():
                        is_abbrev = True

                # Check for known abbreviation
                if not is_abbrev:
                    word_match = re.search(r"([a-zA-Z\.]+)$", paragraph_text[start:punct_idx + 1])
                    if word_match:
                        word = word_match.group(1).lower()
                        if word in COMMON_ABBREVIATIONS or ("." in word[:-1]):
                            is_abbrev = True

            if is_abbrev:
                pos = match_end
                continue

            # Valid sentence boundary found
            raw_sentence = paragraph_text[start:punct_idx + 1]
            sent_str = raw_sentence.strip()
            if sent_str:
                leading_ws = len(raw_sentence) - len(raw_sentence.lstrip())
                actual_start = start + leading_ws
                actual_end = actual_start + len(sent_str)
                sentences.append(
                    TextSegment(
                        segment_id=f"sent_{idx:04d}",
                        start=offset_base + actual_start,
                        end=offset_base + actual_end,
                        text=sent_str,
                        block_type="sentence",
                    )
                )
                idx += 1

            start = match_end
            pos = match_end

        return sentences

    def segment_document(self, text: str) -> List[Tuple[TextSegment, List[TextSegment]]]:
        """
        Segments a full document into structured paragraphs and their constituent sentences.
        Maintains absolute source offsets across the document.
        """
        paragraphs = self.split_paragraphs(text)
        result = []
        for p in paragraphs:
            sents = self.split_sentences(p.text, offset_base=p.start)
            result.append((p, sents))
        return result
