"""Unit tests for text segmentation and offset tracking."""

import pytest
from canopus_humanizer.engine.segmentation import TextSegmenter


def test_split_paragraphs_preserves_offsets():
    text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph."
    segmenter = TextSegmenter()
    paras = segmenter.split_paragraphs(text)

    assert len(paras) == 3
    for p in paras:
        # Verify offset slice matches text exactly
        assert text[p.start:p.end] == p.text


def test_split_sentences_safeguards_abbreviations():
    text = "Dr. Smith et al. presented the results at 3.14 p.m. in the hall. The discussion followed."
    segmenter = TextSegmenter()
    sentences = segmenter.split_sentences(text)

    assert len(sentences) == 2
    assert "Dr. Smith et al." in sentences[0].text
    assert "3.14 p.m." in sentences[0].text
    assert sentences[1].text == "The discussion followed."


def test_split_sentences_initials():
    text = "J. K. Rowling authored books. They are well known."
    segmenter = TextSegmenter()
    sentences = segmenter.split_sentences(text)

    assert len(sentences) == 2
    assert "J. K. Rowling" in sentences[0].text
    assert sentences[1].text == "They are well known."
