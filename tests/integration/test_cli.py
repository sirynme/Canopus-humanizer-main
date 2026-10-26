"""Integration tests for Canopus CLI commands."""

import json
import pytest
from canopus_humanizer.cli import main


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "4.2.0" in captured.out


def test_cli_validate_rules(tmp_path, capsys):
    rule_file = tmp_path / "test_rule.json"
    rule_file.write_text(json.dumps({
        "schema_version": "1.0",
        "ruleset_id": "cli_test",
        "version": "1.0.0",
        "language": "en",
        "rules": [
            {
                "id": "r1",
                "enabled": True,
                "category": "style",
                "risk": "low",
                "operation": "replace_exact",
                "pattern": "foo",
                "replacement": "bar",
            }
        ]
    }))

    code = main(["validate-rules", str(rule_file)])
    assert code == 0
    captured = capsys.readouterr()
    assert "Ruleset 'cli_test' (v1.0.0) is VALID" in captured.out


def test_cli_metrics(tmp_path, capsys):
    text_file = tmp_path / "sample.txt"
    text_file.write_text("The quick brown fox jumps over the lazy dog.")

    code = main(["metrics", str(text_file)])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["word_count"] == 9
    assert data["sentence_count"] == 1


def test_cli_format_citation(tmp_path, capsys):
    cit_file = tmp_path / "cit.json"
    cit_file.write_text(json.dumps({
        "title": "A Great Study",
        "authors": ["Doe, J."],
        "year": "2024",
        "doi": "10.1000/182"
    }))

    code = main(["format-citation", str(cit_file)])
    assert code == 0
    captured = capsys.readouterr()
    assert "[APA 7th]" in captured.out
    assert "Doe, J. (2024). A Great Study." in captured.out


def test_cli_transform(tmp_path, capsys):
    input_file = tmp_path / "input.txt"
    output_file = tmp_path / "output.txt"
    input_file.write_text("Due to the fact that we test, we succeed.")

    code = main(["transform", str(input_file), "-r", "base", "-o", str(output_file), "--diff"])
    assert code == 0
    assert output_file.exists()
    out_content = output_file.read_text()
    assert "Because we test, we succeed." in out_content
