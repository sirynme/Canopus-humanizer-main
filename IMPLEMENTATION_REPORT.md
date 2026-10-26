# Canopus Humanizer — Core Engine Implementation Report

**Document Version:** 1.0.0  
**Engine Version:** 1.0.0  
**Date:** 26 October 2026  
**Status:** Complete & Verified  

---

## 1. Executive Summary

In accordance with the requirements defined in `Core_Engine_A_to_Z.md`, the functional **Canopus Humanizer Core Engine** has been designed, implemented, integrated, and verified within the workspace.

The resulting system is a deterministic, reviewable, modular text-transformation engine. It replaces heuristics and unvalidated replacements with a strict 10-stage execution pipeline, structured rule governance, multi-domain protected span preservation, format adapters, and comprehensive security boundaries.

All 90 automated unit, property-based, security, integration, and regression tests pass cleanly.

---

## 2. Architecture & Module Breakdown

The implemented source tree strictly mirrors the modular boundaries established in Section 3 of `Core_Engine_A_to_Z.md`:

```text
backend/src/canopus_humanizer/
├── __init__.py               # Exports Pipeline, TransformRequest, TransformResult, etc.
├── cli.py                    # CLI commands: transform, validate-rules, metrics, format-citation
├── engine/
│   ├── errors.py             # Typed exceptions & standardized error codes
│   ├── models.py             # Immutable dataclasses: TransformRequest, Change, TransformResult, etc.
│   ├── protected_spans.py    # Multi-domain span detector & nonce-masking registry
│   ├── segmentation.py       # Sentence/paragraph segmenter with source offset tracking
│   ├── planner.py            # Deterministic conflict resolver & change planner
│   ├── transforms.py         # Exact, regex, and redundancy transform operations
│   ├── validation.py         # Structural, numeric, and negation safeguards
│   ├── diff.py               # Unified diff generator & change formatter
│   └── pipeline.py           # 10-stage execution pipeline coordinator
├── rules/
│   ├── schema.py             # Versioned JSON schema validation (v1.0)
│   ├── loader.py             # Cryptographic SHA-256 hashing & safe rule parsing
│   └── registry.py           # Rule pack registry & priority resolver
├── adapters/
│   ├── base.py               # Abstract adapter contract
│   ├── plain_text.py         # UTF-8 plain-text adapter with no-op mode
│   ├── docx.py               # Word DOCX adapter with round-trip re-verification
│   ├── latex.py              # LaTeX adapter with preamble shielding & brace checks
│   └── code_comments.py      # Language-aware comment adapter (Python, C, C++, Java, JS/TS, Go)
├── citations/
│   ├── formatters.py         # APA 7th, IEEE, BibTeX, Chicago style formatters
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

## 3. Ten-Stage Execution Pipeline Implementation

The pipelinse coordinates transformations deterministically through ten discrete phases:

1. **Stage 1 — Input Validation & Normalization**:
   - Inspects byte count, character count, and encoding.
   - Detects and rejects illegal NUL bytes.
   - Standardizes line breaks while tracking original offsets.

2. **Stage 2 — Protected Span Detection**:
   - Multi-tier detection covering:
     - Math (display `$$...$$`, `\[...\]`, inline `$f(x)$`, `\(...\)`).
     - LaTeX environments (`\begin{...}...\end{...}`) and balanced macros (`\frac{...}{...}`, `\cite{...}`).
     - Citations (APA `(Author et al., 2024)`, IEEE `[1]`, `[1-3]`).
     - Numbers, decimals, percentages, dates, currencies (`$25.00`, `$4.5 million`, `98.6%`, `2024`).
     - Physical units (`10 kg`, `25 ms`, `100 km`, `4.2 GHz`, `35 °C`, `100 queries per second`).
     - URLs, email addresses, DOIs (`https://...`, `user@example.com`, `10.1000/182`).
     - Code blocks (Markdown fenced blocks, inline backtick code).
     - Quoted passages (`"exact words"`, `“...”`, `«...»`).
     - Technical terms & custom user glossary terms.
   - Overlap resolution: larger structural spans take precedence over inner tokens.

3. **Stage 3 — Nonce-Based Masking**:
   - Generates collision-resistant placeholders (`<<CANOPUS_PROT_{span_id}_{nonce}>>`).
   - Masks protected spans from right-to-left to prevent offset drift.

4. **Stage 4 — Deterministic Planning & Conflict Resolution**:
   - Finds all candidate rule matches across eligible text.
   - Rejects candidate edits that touch or intersect protected spans or placeholders.
   - Deterministic sorting: Priority DESC, Start Offset ASC, Match Length DESC, Rule ID ASC.
   - Resolves overlaps: higher priority wins; lower-priority conflicting rules are recorded as `RULE_CONFLICT`.
   - Enforces `max_changes` budget.

5. **Stage 5 — Reverse-Offset Transformation**:
   - Applies approved edits from highest offset down to lowest offset, ensuring zero offset drift without mutating the original buffer.

6. **Stage 6 — Protected Span Restoration with Fail-Closed Verification**:
   - Pre-restoration check: verifies each generated placeholder exists in the transformed text exactly once.
   - If any placeholder is missing or duplicated, restoration immediately triggers fail-closed rollback to the original raw text.
   - Restores exact original characters.

7. **Stage 7 — Factual, Semantic & Structural Validation**:
   - Exact protected span equality check.
   - Number and currency preservation: guarantees no numbers are dropped or altered.
   - Negation preservation: detects added or removed negation words (`not`, `never`, `cannot`, etc.).
   - Modal certainty drift: flags shifts between certainty (`must`, `proven`) and uncertainty (`may`, `plausible`).
   - Paragraph count integrity.

8. **Stage 8 — Unified Diff & Change Audit**:
   - Generates unified diff between original and final text.
   - Formats human-reviewable change logs with offsets, categories, and review flags.

9. **Stage 9 — Descriptive Metrics**:
   - Computes character count, word count, sentence count, sentence length std dev (burstiness), Type-Token Ratio (vocabulary richness), Flesch Reading Ease, Flesch-Kincaid Grade Level, zlib compression ratio, and Shannon entropy.
   - Appends mandatory disclaimer stating text statistics do not prove authorship or AI generation.

10. **Stage 10 — Acceptance Gate & Privacy-Preserving Logging**:
    - Sets `accepted = True` only if all validation stages pass.
    - Emits structured JSON audit event recording metadata, timing, and rule counts without logging raw document text.

---

## 4. Rule Governance & Bundled Rule Packs

Rules are stored as versioned JSON data following strict schema validation:
- Schema fields: `schema_version`, `ruleset_id`, `version`, `language`, and `rules[]`.
- Rule fields: `id`, `enabled`, `category`, `risk`, `operation`, `pattern`, `replacement`, `case_sensitive`, `priority`, `requires_review`, `preserve_case`, and `source_note`.

Three validated rule packs are deployed in `rulesets/`:
1. `rulesets/base.json`:
   - 10 clarity, redundancy, and style rules (e.g. "due to the fact that" -> "because", "in order to" -> "to", "takes into account" -> "considers").
2. `rulesets/academic.json`:
   - 10 scholarly style and phrase rules (e.g. "this research paper" -> "the present work", "previous studies have shown" -> "prior investigations have shown", "delve into" -> "examine closely", "stands as a testament to" -> "demonstrates the efficacy of").
3. `rulesets/technical.json`:
   - 6 technical writing rules, terminology locks (locks "learning rate", "gradient descent"), and precision phrasing.

---

## 5. Format Adapters

- **Plain Text (`PlainTextAdapter`)**: UTF-8 input/output, paragraph preservation, unified diff, and no-op mode.
- **DOCX (`DocxAdapter`)**: Inspects archive headers, parses paragraphs and table cells, preserves run formatting, saves to in-memory bytes, and re-opens to verify package integrity.
- **LaTeX (`LatexAdapter`)**: Protects preamble before `\begin{document}`, preserves math environments and macros, and verifies curly brace balance (`{` and `}`) before and after transformation.
- **Code Comments (`CodeCommentAdapter`)**: Language-aware lexer distinguishing comments from string literals for Python (`#`), C/C++/Java/JS/TS/Go (`//`, `/* ... */`). Transforms only comment text and verifies that non-comment code syntax is 100% byte-for-byte identical.

---

## 6. Citations & Reference Module

- **Formatting (`CitationFormatter`)**: Generates APA 7th, IEEE, and BibTeX entries with proper LaTeX escaping (`\&`, `\%`, `\_`, `\$`, `\#`).
- **Validation (`CitationValidator`)**: Validates DOI syntax, required fields, and explicitly flags verification status (`formatted`, `metadata_checked`, `not_verified` for offline operation).

---

## 7. Security Safeguards

- **ReDoS Prevention**: Constrains regex pattern length and detects nested quantifiers `(a+)+` to reject catastrophic backtracking.
- **Archive Bomb Protection**: Inspects ZIP/DOCX archives before extraction, enforcing limits on decompression ratio (`max_decompression_ratio = 10.0`), total uncompressed bytes (25MB), and entry count (500).
- **Directory Traversal Defense**: Rejects parent directory sequences (`../`), absolute paths, Windows drive prefixes, and NUL bytes in file and archive paths.
- **Privacy Assurance**: Memory-only processing with guaranteed cleanup of temporary resources; operational audit logs do not store document contents.

---

## 8. Backward Compatibility & Integration

- The existing FastAPI launcher `backend/run_api.py` and frontend in `docs/index.html` remain 100% functional.
- The `/v1/humanize` and `/v1/health` endpoints continue to be served without breaking changes.
- New endpoints added:
  - `POST /v1/transform`: Full Canopus transformation API.
  - `GET /v1/rulesets`: Catalog of registered rule packs, versions, and SHA-256 hashes.
  - `POST /v1/citations/format`: Citation formatting and metadata validation.

---

## 9. Specification Deviations & Technical Rationales

1. **Package Namespace Coexistence**:
   - *Specification suggested:* Module structure starting with `canopus_humanizer/`.
   - *Implementation:* Created `backend/src/canopus_humanizer/` as the primary engine package, added `canopus` console script to `pyproject.toml`, and integrated with `canopus_humanizer` so both direct engine imports and the existing web application work seamlessly.
2. **Deterministic Default**:
   - The original repository code had randomized thresholds in `modifier.py`. The new core engine replaces probabilistic firing with deterministic priority sorting and conflict resolution, reserving `seed` for optional explicit stochastic behavior.
