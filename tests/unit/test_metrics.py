"""Unit tests for text metrics, compression ratio, entropy, and readability."""

import pytest
from canopus_humanizer.metrics.metrics import TextMetricsCalculator


def test_metrics_calculation_battery():
    text = (
        "The quick brown fox jumps over the lazy dog. "
        "Furthermore, academic writing requires careful inspection of statistical metrics. "
        "In modern computational environments, deterministic testing is paramount."
    )
    calculator = TextMetricsCalculator()
    res = calculator.calculate(text)

    assert res.word_count > 20
    assert res.sentence_count == 3
    assert res.paragraph_count == 1
    assert res.avg_sentence_length > 0
    assert 0.0 < res.type_token_ratio <= 1.0
    assert 0.0 < res.zlib_compression_ratio <= 2.0
    assert res.shannon_entropy > 0.0
    assert "Notice: Text statistics" in res.disclaimer


def test_metrics_empty_text():
    calculator = TextMetricsCalculator()
    res = calculator.calculate("")
    assert res.word_count == 0
    assert res.sentence_count == 0
    assert res.shannon_entropy == 0.0
