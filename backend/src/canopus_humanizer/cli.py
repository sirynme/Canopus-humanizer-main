"""Command-Line Interface (CLI) for Canopus Humanizer."""

import argparse
import json
import sys
from pathlib import Path

from canopus_humanizer.adapters.code_comments import CodeCommentAdapter
from canopus_humanizer.adapters.docx import DocxAdapter
from canopus_humanizer.adapters.latex import LatexAdapter
from canopus_humanizer.adapters.plain_text import PlainTextAdapter
from canopus_humanizer.citations.formatters import CitationFormatter
from canopus_humanizer.citations.validation import CitationValidator
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.metrics.metrics import TextMetricsCalculator
from canopus_humanizer.rules.loader import RulesetLoader
from canopus_humanizer.rules.registry import RuleRegistry


ENGINE_VERSION = "1.0.0"


def cmd_transform(args: argparse.Namespace) -> int:
    """Executes file transformation."""
    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: Input file '{args.file}' not found.", file=sys.stderr)
        return 1

    registry = RuleRegistry()
    pipeline = Pipeline(registry=registry, version=ENGINE_VERSION)
    ruleset_ids = tuple(args.ruleset or ["base"])

    fmt = args.format.lower()
    if fmt == "auto":
        suffix = input_path.suffix.lower()
        if suffix in (".docx",):
            fmt = "docx"
        elif suffix in (".tex", ".latex"):
            fmt = "latex"
        elif suffix in (".py", ".c", ".cpp", ".java", ".js", ".ts", ".go"):
            fmt = "code_comments"
        else:
            fmt = "plain_text"

    try:
        if fmt == "docx":
            adapter = DocxAdapter()
            raw_bytes = input_path.read_bytes()
            req = TransformRequest(text="", mode=args.mode, ruleset_ids=ruleset_ids)
            out_bytes, res = adapter.transform(raw_bytes, pipeline=pipeline, request=req)
            if args.out:
                Path(args.out).write_bytes(out_bytes)
                print(f"Successfully wrote transformed DOCX to {args.out}")
            else:
                print(f"DOCX processed: {len(res.changes)} transformations applied. Use --out to save.")

        elif fmt == "latex":
            adapter = LatexAdapter()
            raw_text = input_path.read_text(encoding="utf-8")
            req = TransformRequest(text=raw_text, mode=args.mode, ruleset_ids=ruleset_ids)
            out_text, res = adapter.transform(raw_text, pipeline=pipeline, request=req)
            if args.out:
                Path(args.out).write_text(out_text, encoding="utf-8")
                print(f"Successfully wrote transformed LaTeX to {args.out}")
            else:
                print(out_text)

        elif fmt == "code_comments":
            adapter = CodeCommentAdapter()
            raw_text = input_path.read_text(encoding="utf-8")
            lang = args.lang or input_path.suffix.lstrip(".").lower()
            req = TransformRequest(text=raw_text, mode=args.mode, ruleset_ids=ruleset_ids)
            out_text, res = adapter.transform(raw_text, pipeline=pipeline, language=lang, request=req)
            if args.out:
                Path(args.out).write_text(out_text, encoding="utf-8")
                print(f"Successfully wrote transformed code to {args.out}")
            else:
                print(out_text)

        else:
            adapter = PlainTextAdapter()
            raw_text = input_path.read_text(encoding="utf-8")
            req = TransformRequest(text=raw_text, mode=args.mode, ruleset_ids=ruleset_ids)
            out_text, res = adapter.transform(raw_text, pipeline=pipeline, request=req, no_op=args.no_op)
            if args.out:
                Path(args.out).write_text(out_text, encoding="utf-8")
                print(f"Successfully wrote transformed text to {args.out}")
            else:
                print(out_text)

        if args.diff and res.diff:
            print("\n--- UNIFIED DIFF ---")
            print(res.diff)

        print(f"\n[Summary] Accepted: {res.accepted} | Changes: {len(res.changes)} | Issues: {len(res.issues)}")
        return 0 if res.accepted else 2

    except Exception as e:
        print(f"Engine Error: {e}", file=sys.stderr)
        return 1


def cmd_validate_rules(args: argparse.Namespace) -> int:
    """Validates a rule pack JSON against schema."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: Rule file '{args.file}' not found.", file=sys.stderr)
        return 1

    try:
        rs = RulesetLoader.load_from_file(path)
        print(f"Ruleset '{rs.ruleset_id}' (v{rs.version}) is VALID.")
        print(f"  Schema version: {rs.schema_version}")
        print(f"  Language:       {rs.language}")
        print(f"  Rules count:    {len(rs.rules)}")
        print(f"  Content hash:   {rs.content_hash}")

        # Category summary
        categories = {}
        for r in rs.rules:
            categories[r.category] = categories.get(r.category, 0) + 1
        print("  Categories:")
        for cat, count in sorted(categories.items()):
            print(f"    - {cat}: {count}")
        return 0

    except Exception as e:
        print(f"Validation FAILED: {e}", file=sys.stderr)
        return 1


def cmd_metrics(args: argparse.Namespace) -> int:
    """Calculates descriptive linguistic and statistical metrics."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8", errors="replace")
    calculator = TextMetricsCalculator()
    res = calculator.calculate(text)

    print(json.dumps(res.to_dict(), indent=2))
    return 0


def cmd_format_citation(args: argparse.Namespace) -> int:
    """Formats and checks reference metadata."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: Citation metadata file '{args.file}' not found.", file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    validator = CitationValidator()
    meta = validator.validate_metadata(data)

    formatter = CitationFormatter()
    print("=== FORMATTED CITATIONS ===")
    print(f"\n[APA 7th]\n{formatter.format_apa(data)}")
    print(f"\n[IEEE]\n{formatter.format_ieee(data)}")
    print(f"\n[BibTeX]\n{formatter.format_bibtex(data)}")
    print("\n=== VALIDATION & PROVENANCE ===")
    print(f"Status: {meta.status}")
    for n in meta.validation_notes:
        print(f"  - {n}")
    return 0


def main(argv=None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="canopus-humanizer",
        description="Canopus Humanizer — Deterministic Rule-Based Text Processing Engine",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {ENGINE_VERSION}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: transform
    p_trans = subparsers.add_parser("transform", help="Transform a document using deterministic rulesets")
    p_trans.add_argument("file", help="Input file path")
    p_trans.add_argument("-r", "--ruleset", action="append", help="Ruleset ID to apply (e.g. base, academic, technical)")
    p_trans.add_argument("-m", "--mode", choices=["conservative", "standard", "manual_review"], default="conservative", help="Transformation aggressiveness mode")
    p_trans.add_argument("-f", "--format", choices=["auto", "plain_text", "docx", "latex", "code_comments"], default="auto", help="Input format adapter")
    p_trans.add_argument("-o", "--out", help="Write output to specified file path")
    p_trans.add_argument("-d", "--diff", action="store_true", help="Print unified diff")
    p_trans.add_argument("--no-op", action="store_true", help="Execute in no-op validation mode without mutating text")
    p_trans.add_argument("--lang", help="Programming language (for code_comments format)")
    p_trans.set_defaults(func=cmd_transform)

    # Subcommand: validate-rules
    p_val = subparsers.add_parser("validate-rules", help="Validate a rule pack against the strict Canopus schema")
    p_val.add_argument("file", help="Path to ruleset JSON file")
    p_val.set_defaults(func=cmd_validate_rules)

    # Subcommand: metrics
    p_met = subparsers.add_parser("metrics", help="Calculate descriptive readability, entropy, and length metrics")
    p_met.add_argument("file", help="Input text file path")
    p_met.set_defaults(func=cmd_metrics)

    # Subcommand: format-citation
    p_cit = subparsers.add_parser("format-citation", help="Validate and format reference metadata into APA, IEEE, and BibTeX")
    p_cit.add_argument("file", help="JSON file containing citation metadata")
    p_cit.set_defaults(func=cmd_format_citation)

    parsed = parser.parse_args(argv)
    return parsed.func(parsed)


if __name__ == "__main__":
    sys.exit(main())
