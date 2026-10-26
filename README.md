# Canopus Humanizer — Core Engine

A deterministic, testable, modular text-processing engine that transforms user-authorized text while preserving meaning, factual details, citations, equations, code, and document structure.

---

## 1. Core Principles & Philosophy

- **Deterministic & Reviewable**: Identical inputs with fixed rule packs and configurations produce byte-for-byte identical outputs.
- **Fail-Closed Protection**: Academic citations (APA, IEEE), LaTeX equations, balanced macros, numeric values, percentages, calendar years, physical units, URLs, and source code are shielded before transformations. If any protected span is dropped or corrupted, the engine safely rolls back.
- **Auditable & Reversible**: Every mutation records rule ID, category, offset range, and before/after text. A unified diff and audit report accompany every transformation.
- **Honest Metrics**: Includes descriptive readability, Shannon entropy, and compression metrics with explicit disclaimers that surface token distributions do not establish authorship or AI generation.
- **Zero Fabrication**: Never invents facts, citations, sources, or quotes.

---

## 2. Installation & Quick Start

### 2.1 Virtual Environment & Dependencies

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package and dependencies
pip install -r requirements.txt
pip install -e .
```

### 2.2 Run Tests

```bash
# Execute unit, property, security, and integration test suites
pytest -v
```

---

## 3. Command-Line Interface (CLI)

The CLI binary `canopus` is available upon installation:

```bash
# Check version
canopus --version

# Transform a document using conservative base and academic rulesets
canopus transform document.txt -r base -r academic --diff

# Transform and save to output file
canopus transform paper.tex -r academic -o paper_transformed.tex

# Transform source code comments only (preserving code syntax 100%)
canopus transform script.py -r base -o script_transformed.py

# Transform a Word document
canopus transform report.docx -r base -o report_transformed.docx

# Run in no-op validation mode (validates protected spans and outputs without mutations)
canopus transform document.txt --no-op

# Validate a rule pack against the strict Canopus JSON schema
canopus validate-rules rulesets/academic.json

# Calculate descriptive linguistic, entropy, and readability metrics
canopus metrics document.txt

# Format and check reference metadata
canopus format-citation citation.json
```

---

## 4. Programmatic Python API

```python
from canopus_humanizer.engine.models import TransformRequest
from canopus_humanizer.engine.pipeline import Pipeline
from canopus_humanizer.rules.registry import RuleRegistry

# Initialize registry and pipeline
registry = RuleRegistry()
pipeline = Pipeline(registry=registry)

# Create request
req = TransformRequest(
    text="Due to the fact that prior studies achieved 98.6% [1], we delve into this research paper.",
    mode="conservative",
    ruleset_ids=("base", "academic"),
    preserve_citations=True,
    preserve_numbers=True,
)

# Process text deterministically
result = pipeline.process(req)

print("Accepted:", result.accepted)
print("Transformed:", result.transformed_text)
# Output: "Because prior studies achieved 98.6% [1], we examine closely the present work."

print("Transformations count:", len(result.changes))
for c in result.changes:
    print(f"  - [{c.rule_id}] '{c.before}' -> '{c.after}' at [{c.start}:{c.end}]")

print("\n--- UNIFIED DIFF ---")
print(result.diff)
```

### 4.1 Using Format Adapters

```python
# DOCX Adapter
from canopus_humanizer.adapters.docx import DocxAdapter

adapter = DocxAdapter()
with open("paper.docx", "rb") as f:
    raw_docx = f.read()

out_docx_bytes, res = adapter.transform(raw_docx, pipeline=pipeline)
with open("paper_transformed.docx", "wb") as f:
    f.write(out_docx_bytes)
```

```python
# LaTeX Adapter
from canopus_humanizer.adapters.latex import LatexAdapter

latex_adapter = LatexAdapter()
with open("paper.tex", "r", encoding="utf-8") as f:
    tex_content = f.read()

out_tex, res = latex_adapter.transform(tex_content, pipeline=pipeline)
```

```python
# Code Comments Adapter (Python, C, C++, Java, JS/TS, Go)
from canopus_humanizer.adapters.code_comments import CodeCommentAdapter

code_adapter = CodeCommentAdapter()
out_code, res = code_adapter.transform(py_code, pipeline=pipeline, language="python")
```

---

## 5. FastAPI Backend & Web Interface

The engine provides a high-performance REST API and serves the included two-pane web interface:

```bash
# Start backend server (default: http://127.0.0.1:8080)
python backend/run_api.py
```

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/health` | Service liveness probe and engine metadata |
| `GET` | `/v1/rulesets` | List registered rule packs, versions, and SHA-256 hashes |
| `POST` | `/v1/transform` | Complete Canopus transformation with diff, metrics, and changes |
| `POST` | `/v1/citations/format` | Format reference metadata into APA 7th, IEEE, BibTeX |
| `POST` | `/v1/humanize` | Backward-compatible endpoint for existing frontend UI |
| `GET` | `/docs` | Interactive Swagger / OpenAPI documentation |

### Interactive Web UI

When the backend server is running, navigate to `http://localhost:8080` in any web browser to access the responsive two-pane editing interface.

---

## 6. Architecture & Module Boundaries

```text
backend/src/canopus_humanizer/
├── __init__.py               # Engine entry point & exports
├── cli.py                    # Command-line interface
├── engine/
│   ├── errors.py             # Typed error hierarchy & codes
│   ├── models.py             # Data contracts (TransformRequest, Change, etc.)
│   ├── protected_spans.py    # Multi-domain span detector & nonce-masking registry
│   ├── segmentation.py       # Sentence/paragraph segmenter with offset tracking
│   ├── planner.py            # Deterministic conflict resolver & change planner
│   ├── transforms.py         # Exact, regex, and redundancy transform operations
│   ├── validation.py         # Structural, numeric, and negation safeguards
│   ├── diff.py               # Unified diff generator & change formatter
│   └── pipeline.py           # 10-stage execution pipeline
├── rules/
│   ├── schema.py             # Versioned JSON schema validation
│   ├── loader.py             # Cryptographic SHA-256 hashing & rule parsing
│   └── registry.py           # Rule pack registry & priority resolver
├── adapters/
│   ├── base.py               # Abstract adapter contract
│   ├── plain_text.py         # UTF-8 plain-text adapter with no-op mode
│   ├── docx.py               # Word DOCX adapter with round-trip re-verification
│   ├── latex.py              # LaTeX adapter with preamble shielding & brace checks
│   └── code_comments.py      # Language-aware comment adapter
├── citations/
│   ├── formatters.py         # APA, IEEE, BibTeX, Chicago style formatters
│   └── validation.py         # Reference metadata and identifier checks
├── metrics/
│   └── metrics.py            # Flesch, Flesch-Kincaid, entropy, compression ratio
├── security/
│   ├── limits.py             # Resource boundaries & ReDoS prevention
│   ├── archive.py            # ZIP-bomb & archive traversal safeguards
│   └── paths.py              # Directory traversal defenses
└── observability/
    └── audit.py              # Privacy-preserving structured JSON audit logger
```

---

## 7. Security & Privacy Safeguards

- **ReDoS Prevention**: Regular expression length is constrained, and catastrophic nested quantifiers are rejected before compilation.
- **Archive Protection**: Decompression ratios, total uncompressed size, and entry counts in DOCX/ZIP files are strictly bounded to prevent decompression bombs.
- **Path Traversal Defenses**: All file paths and archive entry names are inspected to reject relative parent sequences (`../`), absolute paths, and null bytes.
- **Privacy Assurance**: Operational audit logs record request IDs, rule counts, and latencies without logging raw document text.

---

## 8. License

All rights reserved.
