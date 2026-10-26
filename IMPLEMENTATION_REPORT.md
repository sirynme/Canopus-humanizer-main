# Canopus Humanizer — Core Engine Implementation Report

**Document Version:** 4.1.0  
**Engine Version:** 4.0.0 (v1.0.0-compatible)  
**Date:** 26 October 2026  
**Status:** Complete, Verified, Benchmarked & Audited  

---

## 1. Executive Summary

In accordance with the requirements of the **Canopus Humanizer V4 — Engine Quality Overhaul**, the engine has been upgraded from v3 into a robust, high-quality academic and technical editing engine.

The V4 engine prioritizes clarity, grammar, coherence, concision, and natural expression while strictly preserving authorial meaning, technical precision, and factual integrity. It explicitly rejects detector-evasion optimizations in favor of verified writing-quality enhancements, context-aware rule execution, fail-closed validation, and an independent benchmark harness.

All 115 automated unit, integration, property, security, pipeline stage, and benchmark invariant tests pass cleanly (100% success rate, 0 failures, 1 deprecation warning).

---

## 2. Architecture & Module Breakdown

The engine is organized into modular, testable, and independently configurable components:

```text
backend/src/canopus_humanizer/
|-- __init__.py               # Package exports: Pipeline, TransformRequest, TransformResult, etc.
|-- cli.py                    # CLI commands: transform, validate-rules, metrics, format-citation
|-- engine/
|   |-- errors.py             # Standardized error codes & exception hierarchy
|   |-- models.py             # Immutable dataclasses: TransformRequest, Change, TransformResult
|   |-- normalization.py      # Stage 1: Resource limits, NUL byte rejection, NFC normalization
|   |-- classifier.py         # Stage 2: Document style classification & editing need analyzer
|   |-- protected_spans.py    # Nonce-based span masking & restoration registry
|   |-- segmentation.py       # Stage 3: Sentence and paragraph segmenter with source offsets
|   |-- opportunity.py        # Stage 4: Editing opportunity detector (suppresses churn on clear text)
|   |-- providers.py          # Stage 5: Deterministic core provider & optional model interface
|   |-- planner.py            # Deterministic conflict resolver & budget enforcer
|   |-- transforms.py         # Context-aware mutations (capitalization, transition commas, word deduplication)
|   |-- validation.py         # Stage 6: Semantic, directional polarity, numeric & negation safeguards
|   |-- diff.py               # Unified diff generator & change formatter
|   +-- pipeline.py           # 8-stage modular execution pipeline coordinator
|-- rules/
|   |-- schema.py             # Versioned JSON schema validation (v1.0)
|   |-- loader.py             # Cryptographic SHA-256 hashing & safe rule parsing
|   +-- registry.py           # Rule pack registry & priority resolver
|-- adapters/
|   |-- base.py               # Abstract adapter contract
|   |-- plain_text.py         # UTF-8 plain-text adapter with no-op mode
|   |-- docx.py               # Word DOCX adapter with round-trip re-verification
|   |-- latex.py              # LaTeX adapter with preamble shielding & brace checks
|   +-- code_comments.py      # Language-aware comment adapter (Python, C, C++, Java, JS/TS, Go)
|-- citations/
|   |-- formatters.py         # APA 7th, IEEE, BibTeX, Chicago style formatters
|   +-- validation.py         # Reference metadata and identifier checks
|-- metrics/
|   +-- metrics.py            # Flesch, Flesch-Kincaid, entropy, compression ratio
|-- security/
|   |-- limits.py             # Resource boundaries & ReDoS prevention
|   |-- archive.py            # ZIP-bomb & archive traversal safeguards
|   +-- paths.py              # Directory traversal defenses
+-- observability/
    +-- audit.py              # Privacy-preserving structured JSON audit logger
```

---

## 3. Eight-Stage Modular Transformation Pipeline

The V4 execution pipeline replaces unconstrained substitutions with eight explicit, auditable stages:

1. **Stage 1 — Input Validation and Normalization (`normalization.py`)**:
   - Validates character, byte, and line boundaries against configured `ResourceLimits`.
   - Rejects prohibited NUL bytes (`0x00`) with standardized `NUL_BYTE_DETECTED` code.
   - Normalizes Unicode into canonical composed form (NFC).
   - Strips invisible control characters, zero-width spaces (`U+200B-U+200D`), and deceptive bidi overrides while preserving whitespace structure (`\t`, `\n`, `\r`).

2. **Stage 2 — Document and Content-Type Classification (`classifier.py`)**:
   - Classifies document genre into `academic`, `technical`, `general_essay`, or `code_comment`.
   - Analyzes specific editing needs: `grammar`, `redundancy`, `awkward_phrasing`, and `transitions`.
   - Evaluates `is_already_clear`: passages with proper sentence length and zero awkward/redundant patterns are tagged as clear to prevent unnecessary edits.

3. **Stage 3 — Sentence and Paragraph Segmentation (`segmentation.py`)**:
   - Segments multi-paragraph documents into constituent paragraphs and sentences with exact absolute offset mapping.
   - Safeguards Latin abbreviations (`et al.`, `e.g.`, `i.e.`, `Dr.`), initials, and sentence boundaries.

4. **Stage 4 — Identification of Specific Editing Opportunities (`opportunity.py`)**:
   - Evaluates candidate transformations against document classification and selected mode (`conservative` vs `standard`).
   - Suppresses stylistic replacements on clear sentences.
   - Filters out high-risk or manual-review transformations in conservative mode.

5. **Stage 5 — Context-Aware Candidate Revision (`transforms.py`, `providers.py`)**:
   - Detects sentence-initial boundaries to ensure capitalized replacement words (`In order to` -> `To`).
   - Injects required punctuation after introductory transitional adverbs (`Importantly, this` rather than `Importantly this`).
   - Prevents adjacent word duplications (e.g., prevents `To to`).
   - Pluggable editing provider architecture: executes default deterministic rule provider with zero network overhead, supporting an optional model provider interface with strict timeout and fallback.

6. **Stage 6 — Semantic and Structural Validation (`validation.py`)**:
   - Pre-restoration verification: verifies that all nonce-based protected span placeholders (`<<CANOPUS_PROT_{span_id}_{nonce}>>`) are present and uncorrupted.
   - Exact restoration of citations, equations, code, numbers, units, and URLs.
   - Factual invariant checks:
     - Numeric preservation: ensures no numbers or percentages are altered or dropped.
     - Negation preservation: flags added or removed negation words (`not`, `never`, `without`, `cannot`).
     - Modal certainty drift: flags unauthorized shifts between certainty (`must`, `proven`) and uncertainty (`may`, `plausible`).
     - Directional polarity check: detects inadvertent inversion between positive and negative findings (`increase` vs `decrease`, `outperform` vs `underperform`).

7. **Stage 7 — Acceptance, Rejection, or Conservative Fallback**:
   - If any validation error or placeholder corruption occurs, the pipeline fails closed, rolling back entirely to the original input text.
   - Accepted revisions advance to diffing and metrics generation.

8. **Stage 8 — Output Assembly and Change Reporting (`diff.py`, `metrics.py`, `audit.py`)**:
   - Formats unified diffs between original and transformed text.
   - Calculates readability (Flesch, Flesch-Kincaid), Shannon entropy, and compression ratios.
   - Records structured JSON audit events without storing sensitive document content.

---

## 4. Rule Governance & Bundled Rule Packs

Rule packs are stored in `rulesets/` and validated against JSON Schema v1.0:
1. `rulesets/base.json` (30 rules): Redundancy pruning, phrase clarity, modal circumlocution replacement.
2. `rulesets/academic.json` (25 rules): Scholarly register refinement, literature review phrase modernizations, academic verb conversions.
3. `rulesets/technical.json` (14 rules): Technical precision, compute/memory quantifier standardization, terminology locks (`learning rate`, `backpropagation`, `gradient descent`).
4. `rulesets/grammar.json` (12 rules): Standard academic grammar and subject-verb agreement corrections (`irregardless` -> `regardless`, `could of` -> `could have`, `criteria is` -> `criteria are`, `comprise of` -> `comprise`).

---

## 5. Evaluation Benchmark Harness

A version-controlled benchmark suite (`tests/benchmark/`) evaluates original, legacy, and V4 engines across 7 representative test samples (`tests/benchmark/benchmark_samples.json`):
- `academic_literature_review_01`: Formulaic literature review phrases with APA citations and percentages.
- `technical_algorithms_02`: Stochastic gradient descent, LaTeX math ($10^{-4}$), and IEEE citations.
- `general_essay_argument_03`: Redundant cliches and introductory adverb punctuation.
- `clear_well_written_passage_04`: Already-clear, concise technical description (graph algorithm).
- `grammar_and_awkward_corrections_05`: Common grammatical flaws (`irregardless`, `could of`, `criteria is`).
- `multi_paragraph_long_document_06`: 3-paragraph document verifying boundaries and cross-paragraph invariants.
- `citations_equations_terminology_heavy_07`: Heavy equations, loss functions, percentages, negations.

### Summary of Benchmark Results (Measured on Test Corpus)
*Note: These figures represent observed benchmark metrics on the specified 7-sample evaluation corpus and do not constitute an unconstrained universal guarantee for arbitrary input text.*

- **Preservation Rate**: 100.0% of protected spans (citations, LaTeX math, percentages, numbers, URLs) preserved across all 7 benchmark samples.
- **Transformation Rate on Opportunities**: 100.0% of targeted flaws corrected.
- **Unnecessary Edits on Clear Text**: Exactly 0 changes made by V4 on clear text samples (legacy engine made 16 unnecessary changes on sample 04 and 24 on sample 07).
- **Grammar Errors Corrected**: V4 successfully resolved 100% of tested grammatical errors (4 of 4 in sample 05); legacy engine resolved 0%.
- **Punctuation Hygiene**: Fixed introductory adverb spacing (`Importantly, this` vs legacy `Importantly this`).
- **Average Latency**: 6.33ms (sub-10ms for multi-paragraph documents under local execution).

---

## 6. Verification Status & Test Reconciliation

### Exact Pytest Execution Summary
All 115 automated tests passed cleanly (0 failed, 0 skipped, 1 deprecation warning in ~1.5s):

```text
======================== 115 passed, 1 warning in 1.54s ========================
```
*(Warning: `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`)*

### Breakdown by Test Directory
- `tests/unit/`: **78 passed**
  - `test_citations.py`: 3
  - `test_code_comment_adapter.py`: 2
  - `test_diff_and_audit.py`: 3
  - `test_docx_adapter.py`: 1
  - `test_edge_cases_and_adversarial.py`: 4
  - `test_latex_adapter.py`: 2
  - `test_metrics.py`: 2
  - `test_models_and_errors.py`: 4
  - `test_plain_text_adapter.py`: 3
  - `test_planner_and_transforms.py`: 4
  - `test_protected_spans.py`: 6
  - `test_rules_schema_and_loader.py`: 6
  - `test_security_archive.py`: 5
  - `test_security_limits_paths.py`: 10
  - `test_segmentation.py`: 3
  - `test_v4_pipeline_stages.py`: 6
  - `test_v4_robustness.py`: 10
  - `test_validation_and_safeguards.py`: 4
- `tests/integration/`: **22 passed**
  - `test_api_endpoints.py`: 5
  - `test_cli.py`: 5
  - `test_discovered_regressions.py`: 8
  - `test_pipeline_e2e.py`: 4
- `tests/property/`: **5 passed** (`test_engine_properties.py`)
- `tests/security/`: **5 passed** (`test_security_defenses.py`)
- `tests/benchmark/`: **5 passed** (`test_benchmark_invariants.py`)
- **Total: 115 tests**

### Reconciliation of Previous 126 vs 115 Discrepancy
In the initial draft of the implementation report, category counts were listed as:
`Unit tests: 60`, `Integration tests: 17`, `Property-based tests: 5`, `Security & limits tests: 15`, `Benchmark invariant tests: 5`, `V4 pipeline & robustness tests: 16`, `Discovered regression tests: 8` (sum = 126).
The discrepancy arose because functional sub-categories were counted alongside top-level directory counts, resulting in double-counting:
1. The 15 tests under `Security & limits tests` (`test_security_archive.py` [5] + `test_security_limits_paths.py` [10]) are located inside `tests/unit/`.
2. The 16 tests under `V4 pipeline & robustness` (`test_v4_pipeline_stages.py` [6] + `test_v4_robustness.py` [10]) are located inside `tests/unit/`.
3. The 8 tests under `Discovered regression tests` (`test_discovered_regressions.py`) are located inside `tests/integration/`.
When organized strictly by filesystem directory, the physical count is exactly 115 tests (78 unit + 22 integration + 5 property + 5 security + 5 benchmark = 115). No tests were added or removed to reconcile this total.

---

## 7. Assumptions, Verified Scope, and Known Limitations

### Verified Behaviors and Components
- **API Endpoints**: `GET /v1/health`, `GET /v1/rulesets`, `POST /v1/citations/format`, `POST /v1/humanize` (legacy compatibility), and `POST /v1/transform` verified live via FastAPI TestClient.
- **Rule Packs**: Verified all 4 active rulesets (`base` [30 rules], `academic` [25 rules], `technical` [14 rules], `grammar` [12 rules]) load cleanly with valid SHA-256 integrity hashes.
- **Protected Span Invariants**: Proved byte-for-byte preservation of inline math (`$p < 0.05$`), citations (`Smith et al., 2021`), URLs, floats (`0.001`), percentages (`94.2%`), negations (`do not`), and polarity phrases (`under no circumstances`).
- **No-Op Suppression**: Proved 0 changes on already-clear passages.
- **Idempotency**: Proved repeated transformation on previously transformed text yields identical output (`pass1 == pass2`).
- **Safe Fallback**: Proved fail-closed rollback to original input when validation detects corrupted placeholders or semantic boundary violations.

### Known Limitations & Scope Boundaries
- **Lexical/Rule-Based Engine**: The core deterministic provider operates via compiled regex rules, dictionary lookup, and token heuristics. It does not perform deep neural dependency parsing.
- **Protected Span Delimiters**: Nonce masking relies on standard academic syntax patterns (e.g., standard LaTeX delimiters, recognized inline citation conventions, standard numeric notation). Unconventional or malformed syntax may not be shielded by the default span detector.
- **Corpus vs Universal Guarantees**: Benchmark preservation (100%) and error resolution (100%) reflect demonstrated behavior on the 7 benchmark samples and invariant test suite; semantic preservation cannot be guaranteed for arbitrary adversarial text without semantic validation rejecting or accepting.
- **Optional Model Provider**: The interface for neural model providers is defined and tested via mocks, but disabled by default in the deterministic local distribution.
