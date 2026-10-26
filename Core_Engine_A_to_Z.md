# Canopus-Humanizer — Core Engine Specification (A to Z)

**Document type:** Implementation-ready engineering specification  
**Scope:** Core text-transformation engine, rule system, document adapters, validation, testing, and release gates  
**Status:** Proposed target architecture — not a description of verified existing implementation  
**Version:** 1.0  
**Date:** 25 October 2026

---

## 1. Purpose and engineering principles

Canopus-Humanizer is specified here as a deterministic, reviewable text-editing engine. Its job is to transform user-authorized text while preserving meaning, factual details, citations, equations, code, and document structure wherever supported.

The engine must not promise that text will evade plagiarism or AI-writing detectors. It must not fabricate sources, disguise copied work, or present heuristic scores as proof of authorship. Its primary quality goals are transparent editing, traceable changes, format safety, and predictable failure behavior.

### Non-negotiable principles

1. Preserve the original input and never overwrite it in place.
2. Make transformations deterministic for a fixed engine version, rule pack, configuration, and input.
3. Keep transformations separate from parsing, document serialization, and UI.
4. Protect high-risk spans before transforming prose.
5. Record every change with rule ID, location, and before/after text where safe.
6. Validate outputs and fail closed when structure or meaning cannot be safely preserved.
7. Do not invent facts, citations, references, quotes, statistics, or evidence.
8. Distinguish syntax validity from semantic equivalence.
9. Make unsupported file types and structures explicit rather than silently corrupting them.
10. Treat user content and uploaded files as untrusted input.

## 2. Scope and non-goals

### In scope

- Plain-text normalization with explicit, conservative rules.
- Rule-pack loading and validation.
- Protected-span detection and restoration.
- Sentence/paragraph segmentation with offset tracking.
- Optional, rule-driven edits that are reviewable and reversible.
- DOCX and LaTeX adapters with format-specific preservation tests.
- Citation and reference formatting when supplied metadata is available.
- Output validation, diff generation, audit events, and test harnesses.
- Resource limits, safe file handling, and privacy-conscious processing.

### Out of scope unless separately designed and tested

- Guaranteed AI-detector or plagiarism-detector evasion.
- Guaranteed semantic equivalence for arbitrary paraphrases.
- Automated claims that a source supports a statement without source inspection.
- Removal of cryptographic provenance or model-generated watermarks by paraphrasing.
- Full parsing of every programming language, LaTeX package, or Word XML feature.
- Treating compression ratio, character entropy, or readability as an AI-authorship verdict.

## 3. High-level architecture

```text
CLI / UI / API
     |
     v
Input validation and resource limits
     |
     v
Format adapter (plain text / DOCX / LaTeX)
     |
     v
Document model + source-offset map
     |
     v
Protected-span detector and mask registry
     |
     v
Text segmentation
     |
     v
Rule-pack validation and deterministic planner
     |
     v
Transformation pipeline (approved rules only)
     |
     v
Protected-span restoration
     |
     v
Structural + lexical + domain validation
     |
     +---- validation failure ---> reject / revert / request review
     |
     v
Diff + audit record + output serializer
     |
     v
Output file and validation report
```

### Recommended module boundaries

```text
canopus_humanizer/
  __init__.py
  engine/
    pipeline.py
    models.py
    planner.py
    transforms.py
    protected_spans.py
    segmentation.py
    validation.py
    diff.py
    errors.py
  rules/
    loader.py
    schema.py
    registry.py
  adapters/
    base.py
    plain_text.py
    docx.py
    latex.py
  citations/
    formatters.py
    validation.py
  security/
    limits.py
    archive.py
    paths.py
  observability/
    audit.py
  cli.py
tests/
  unit/
  property/
  fixtures/
  integration/
  security/
rulesets/
  base.json
  academic.json
  technical.json
```

This is a proposed structure, not a claim that these files already exist in the uploaded project.

## 4. Core data contracts

Use explicit data models. Do not pass unstructured dictionaries between all components.

### 4.1 Input request

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class TransformRequest:
    text: str
    mode: Literal["conservative", "standard", "manual_review"]
    ruleset_ids: tuple[str, ...]
    language: str = "en"
    preserve_citations: bool = True
    preserve_numbers: bool = True
    preserve_code: bool = True
    seed: int = 0
    max_changes: int = 500
```

The `seed` is reserved for any explicitly supported randomized behavior. The default engine should not require randomness.

### 4.2 Transformation result

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Change:
    rule_id: str
    start: int
    end: int
    before: str
    after: str
    category: str
    requires_review: bool

@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    start: int | None = None
    end: int | None = None

@dataclass(frozen=True)
class TransformResult:
    original_text: str
    transformed_text: str
    changes: tuple[Change, ...]
    issues: tuple[ValidationIssue, ...]
    engine_version: str
    ruleset_versions: tuple[str, ...]
    accepted: bool
```

For confidential content, do not put full text in external logs. Keep detailed diffs local to the processing result and allow users to disable them.

## 5. Input validation and normalization

### Required checks

- Verify input type and encoding.
- Enforce byte, character, paragraph, and processing-time limits.
- Reject or safely report malformed binary input passed as text.
- Normalize line endings consistently, while retaining enough source mapping to reconstruct output.
- Do not silently normalize Unicode characters that may be meaningful in mathematics, identifiers, or other scripts.
- Detect NUL bytes and unexpected control characters.
- Validate selected mode and rule-set IDs against an allowlist.
- Reject unsupported formats with an actionable error.

### Normalization policy

Normalization must be explicit and reversible where possible. Do not globally collapse whitespace or alter punctuation before identifying protected regions. Avoid changing Unicode normalization forms without a documented policy and tests.

## 6. Protected-span model

A protected span is a range that ordinary prose transformations must not alter. Protected spans are registered before any rewrite.

### Typical protected spans

- Numeric values, percentages, dates, units, ranges, and statistical results.
- Names, identifiers, acronyms, product names, defined terms, and user-provided glossary entries.
- URLs, email addresses, DOI strings, and citation keys.
- Inline citations, reference entries, footnote markers, and cross-reference labels.
- LaTeX commands, math environments, equations, code blocks, and inline code.
- Quoted passages that must remain exact.
- File paths, command examples, JSON, YAML, XML, and other structured snippets.
- Explicit user-selected immutable text.

### Span model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ProtectedSpan:
    span_id: str
    start: int
    end: int
    kind: str
    original: str
    detector: str
    confidence: float
```

### Detection requirements

1. Prefer parsers for structured formats over regular expressions.
2. Use regular expressions only for narrow, well-defined tokens.
3. Resolve overlaps using documented precedence, such as whole code block before inline token.
4. Keep original offsets and exact original values.
5. If a span is ambiguous, protect a larger region or stop the transformation.
6. Use unique, collision-resistant placeholders only inside the internal processing representation.
7. Verify every placeholder exists exactly once before restoration.
8. Verify restored protected text matches the original exactly.

Do not assume that a placeholder strategy alone guarantees preservation. Test nested, repeated, malformed, and adversarial inputs.

## 7. Segmentation and offset tracking

Segment text into document blocks, paragraphs, sentences, and eligible prose spans. Keep stable source offsets through every stage.

### Requirements

- Avoid splitting abbreviations, decimal numbers, initials, citations, URLs, and code.
- Keep paragraph and list boundaries unless the selected operation explicitly permits changes.
- Preserve block order.
- Track source ranges for each transformed segment.
- Treat segmentation uncertainty as a validation warning.
- Never use sentence segmentation as evidence that a sentence can be safely rewritten.

## 8. Rule-pack format and governance

Rules are versioned data, not executable code. Do not load arbitrary Python or shell code from a rule file.

### Example rule

```json
{
  "schema_version": "1.0",
  "ruleset_id": "base-en",
  "version": "1.0.0",
  "language": "en",
  "rules": [
    {
      "id": "style.remove_redundant_filler_001",
      "enabled": false,
      "category": "style",
      "risk": "low",
      "operation": "replace_exact",
      "pattern": "due to the fact that",
      "replacement": "because",
      "case_sensitive": false,
      "priority": 100,
      "requires_review": true,
      "preserve_case": true,
      "source_note": "Conservative style edit; user approval required."
    }
  ]
}
```

### Required schema fields

- `schema_version`
- `ruleset_id`
- `version`
- `language`
- `rules[]`
- Each rule: stable `id`, `enabled`, `category`, `risk`, `operation`, `priority`, `requires_review`, and operation-specific fields.

### Loader behavior

- Parse JSON with strict error reporting.
- Validate against a versioned schema.
- Reject duplicate rule IDs and unsupported operations.
- Reject invalid regex syntax and enforce complexity limits if regex rules are supported.
- Disallow filesystem paths, network access, imports, and code execution from rule content.
- Resolve rule precedence deterministically.
- Report counts of loaded, disabled, rejected, and conflicting rules.
- Fail startup if a required ruleset is invalid; do not silently continue with partial critical configuration.
- Record ruleset version and content hash in the transformation result.

### Rule categories

Recommended categories include:

- `formatting`
- `grammar`
- `clarity`
- `redundancy`
- `terminology`
- `citation_format`
- `document_structure`

Do not create rule categories whose sole purpose is bypassing a detector or disguising copied material.

## 9. Transformation pipeline

Each stage must have a clear contract, input/output type, error policy, and tests. The default pipeline should be conservative.

### Stage 1 — Parse and model

Select the format adapter and create a document model. Preserve block types, source offsets, and immutable structures.

### Stage 2 — Detect protected spans

Identify protected text and record it in a registry. Stop if the format parser reports unsafe or incomplete parsing.

### Stage 3 — Segment eligible prose

Create stable segments that exclude protected spans and preserve block boundaries.

### Stage 4 — Plan changes

Match enabled rules against eligible text. Build a change plan before applying it. Resolve overlapping edits by priority and explicit conflict rules.

### Stage 5 — Apply approved edits

Apply edits from the end of the source toward the beginning, or use a robust edit-script abstraction, to avoid offset drift. Never mutate the original input buffer.

### Stage 6 — Restore protected spans

Restore exact originals and verify placeholder integrity. Any missing, duplicated, or altered protected span causes rejection or rollback.

### Stage 7 — Validate output

Run structural checks, protected-span equality checks, number/unit/citation checks, encoding checks, and rule-specific postconditions.

### Stage 8 — Produce diff and report

Return original and transformed output, change list, warnings, validation issues, and engine/ruleset versions. The user must be able to inspect and reject every change.

### Stage 9 — Serialize

The adapter writes output to a new file or in-memory stream. Reopen the output with the same parser where possible and run round-trip checks.

### Stage 10 — Final acceptance

Accept only if required checks pass. If a critical check fails, return the original or a clearly marked partial result; never silently provide a damaged document.

## 10. Rule operation types

Start with a small, auditable operation set:

1. `replace_exact` — literal replacement with explicit case handling.
2. `regex_replace` — optional; restricted patterns, timeouts/limits, and tests required.
3. `remove_redundancy` — only for reviewed, deterministic patterns.
4. `terminology_lock` — protect defined terms rather than rewrite them.
5. `format_citation` — format supplied, verified metadata; do not invent references.
6. `manual_suggestion` — present an edit to the user without applying it automatically.

Avoid a generic “rewrite any sentence” rule operation in the deterministic core. If an external language model is added later, isolate it behind a separate interface, mark its edits as probabilistic, and apply the same protection and validation gates.

## 11. Change conflicts and deterministic planning

Two edits may overlap or compete. The planner must resolve this before mutation.

Recommended policy:

1. Reject edits that touch protected spans.
2. Sort candidates by explicit priority, then start offset, then stable rule ID.
3. Reject overlapping candidates unless a documented composition rule exists.
4. Apply no more than the configured `max_changes`.
5. Record rejected conflicts in the report.
6. Ensure the same input and versions produce the same output.

Never let filesystem order, dictionary iteration assumptions, network response order, or timestamps affect rule selection.

## 12. Semantic and factual safeguards

String-level validation cannot prove that a paraphrase preserves meaning. Therefore, use layered safeguards.

### Automated checks

- Exact preservation of protected tokens.
- Equality of numeric tokens, units, dates, identifiers, citation keys, and URLs where preservation is required.
- Detection of added or removed negation terms.
- Detection of changed modal/qualifying language such as “may,” “must,” “only,” “approximately,” and “significant.”
- Sentence and paragraph count changes when disallowed.
- Domain glossary conformance.
- Citation-marker and reference-count consistency.

### Human review

Require review for edits that affect scientific claims, causal relationships, uncertainty, legal or medical wording, quotations, or technical definitions.

### Acceptance policy

If a rule may alter the proposition or scope of a statement, classify it as review-required. Do not describe a result as “meaning-preserving” solely because protected numbers match.

## 13. Plain-text adapter

The plain-text adapter is the reference implementation.

### Input

UTF-8 text or explicitly supported encodings.

### Output

UTF-8 text plus a structured report.

### Required behavior

- Preserve paragraph breaks by default.
- Preserve protected tokens exactly.
- Provide a unified diff.
- Support no-op mode for validation without transformation.
- Avoid implicit sentence merging/splitting.
- Return a typed error for invalid encoding or resource-limit violation.

## 14. DOCX adapter

DOCX is a ZIP package containing XML parts and related resources. A robust adapter must understand document structure; a simple paragraph-text replacement is not enough.

### Minimum supported structures to test

- Main body paragraphs and runs.
- Tables, nested tables, and cell paragraphs.
- Headers and footers.
- Hyperlinks and external relationships.
- Footnotes/endnotes if supported.
- Fields, bookmarks, comments, and tracked changes.
- Numbered and bulleted lists.
- Images and embedded objects.
- Content controls and text boxes, where supported.

### Implementation rules

- Use a maintained DOCX library for ordinary supported structures.
- Avoid rewriting the entire XML package if only selected text nodes need modification.
- Understand that a phrase may be split across multiple runs because of formatting.
- Preserve relationships and package parts not intentionally changed.
- Reject encrypted, malformed, or unsupported files with a clear message.
- Reopen the generated file and validate package integrity.
- Compare document structure and render representative fixtures to PDF/images for visual regression.

### DOCX acceptance tests

- No unexpected missing paragraphs, tables, relationships, images, or comments.
- Unchanged runs retain formatting in supported cases.
- All protected text remains exact.
- The file opens in independent Word-compatible software.
- Any unsupported feature is reported rather than silently discarded.

Do not claim 100% formatting preservation without a defined compatibility matrix and evidence.

## 15. LaTeX adapter

LaTeX must be handled with an explicit syntax-aware strategy. Arbitrary regular-expression rewriting is unsafe.

### Minimum protected structures

- Commands and their arguments.
- Math delimiters and math environments.
- `\verb` and verbatim-like environments.
- Comments and escaped percent signs.
- Labels, references, citations, URLs, and file paths.
- Custom macros and nested groups.
- Bibliography entries and package-specific constructs.

### Required checks

- Preserve protected commands and math content exactly.
- Track braces and environment boundaries.
- Compile before/after with a controlled test toolchain where available.
- Compare errors and warnings against the baseline.
- Do not execute shell escapes or arbitrary build commands from untrusted input.
- Treat unknown macros and malformed environments as protected or unsupported.

A successful compile does not prove semantic equivalence, but a failed compile is a clear rejection condition for a compile-required workflow.

## 16. Source-code comment adapter

Code-comment editing must be language-aware. A generic regex cannot reliably distinguish comments from string literals across languages.

### Minimum design

- Require an explicit supported-language selection or reliable language detection with user confirmation.
- Use a lexer or parser for each supported language.
- Identify comment nodes and preserve all non-comment tokens exactly.
- Do not rewrite strings, templates, docstrings, directives, annotations, or embedded code unless explicitly supported.
- Reparse, lint, compile, or run tests after edits where tooling is available.
- Compare token streams or ASTs while excluding permitted comment nodes.

### Failure policy

If language detection is uncertain, parsing fails, or the file uses unsupported syntax, leave it unchanged and report why. “Code safety” is established only for a stated language/version/test matrix, never universally.

## 17. Citation and reference module

Separate citation formatting from citation verification.

### Formatting responsibilities

- Format user-supplied metadata into supported styles.
- Validate output syntax for BibTeX, JSON, or LaTeX.
- Escape characters correctly.
- Preserve citation keys and links when required.
- Detect duplicate keys and missing required fields.

### Verification responsibilities

- Resolve DOI or URL where possible.
- Compare returned title, author, date, venue, and identifier with the supplied reference.
- Flag missing, inconsistent, retracted, or unresolvable sources.
- Distinguish `formatted`, `metadata_checked`, `source_opened`, and `claim_supported` states.
- Never label a claim supported solely because a citation exists.

If network verification is unavailable, report “not verified”; do not guess.

## 18. Text metrics and checker module

A checker may provide descriptive measurements, but must accurately name them.

### Possible descriptive metrics

- Character count and token count under a documented tokenizer.
- Sentence and paragraph length distributions.
- Repeated phrase counts.
- Readability estimates with named formulas.
- Compression ratio under a specified compressor.
- Character or token entropy under a defined calculation.
- Citation and protected-span counts.

### Critical distinctions

- **Compression ratio** is compressed size divided by original size under a named compressor and settings.
- **Shannon entropy** measures uncertainty in a defined symbol distribution.
- **Language-model perplexity** derives from token probabilities from a specified language model and tokenizer.
- None of these, alone, establishes who authored a text or whether misconduct occurred.

If the system offers an AI-writing estimate, it requires an independently designed and evaluated model, representative evaluation data, documented limitations, and false-positive/false-negative reporting. Do not use an unvalidated score to accuse a user of misconduct.

## 19. File and archive security

Uploaded files are untrusted.

### Required controls

- Maximum upload size, decompressed size, file count, nesting depth, and processing time.
- Reject archive path traversal (`../`, absolute paths, drive prefixes, and unsafe normalized paths).
- Defend against ZIP bombs and duplicate-name ambiguity.
- Do not extract archives to arbitrary filesystem locations.
- Use safe temporary directories and guaranteed cleanup.
- Validate file signatures in addition to extensions.
- Reject encrypted or malformed packages unless explicitly supported.
- Do not execute macros, scripts, shell commands, or document content.
- Restrict external entity resolution and unsafe XML parser features.
- Keep dependencies patched and scan them in CI.
- Do not log secrets, uploaded text, or full document contents by default.

## 20. Privacy and data lifecycle

A privacy claim must describe the deployed system, not only the core function.

### Data-flow inventory

Document where content may exist in:

- Request memory.
- Temporary files.
- Application logs and exception traces.
- Framework caches and session state.
- Reverse proxies and hosting telemetry.
- Backups and snapshots.
- External APIs or observability providers.

### Minimum requirements

- Collect only data needed for the requested operation.
- Keep text out of logs by default.
- Use TLS in transit and restricted access to operational systems.
- Define retention and deletion behavior for every storage layer.
- Avoid third-party processing unless disclosed and authorized.
- Test temporary-file cleanup on success, exception, timeout, and cancellation.
- Ensure error messages do not expose other users' content or server paths.
- Make the privacy notice match actual configuration.

“In-memory processing” does not by itself prove “zero storage.”

## 21. Error model and observability

Use stable error codes rather than raw exception messages.

Suggested codes:

- `INPUT_INVALID`
- `INPUT_TOO_LARGE`
- `UNSUPPORTED_FORMAT`
- `PARSER_FAILED`
- `RULESET_INVALID`
- `RULE_CONFLICT`
- `PROTECTED_SPAN_MISMATCH`
- `OUTPUT_VALIDATION_FAILED`
- `SERIALIZATION_FAILED`
- `RESOURCE_LIMIT_EXCEEDED`
- `CITATION_UNVERIFIED`

Logs should record request IDs, module/version, duration, error code, rule-pack hash, and aggregate counts. Do not log raw text by default. Separate operational logs from user-visible change reports.

## 22. Performance and resource management

Define limits before optimizing.

- Set maximum bytes, paragraphs, protected spans, candidate edits, and rule count.
- Bound regex execution time or disallow untrusted regex rules.
- Avoid repeated full-document scans where indexed spans suffice.
- Cache parsed rule packs by content hash, not by untrusted filename alone.
- Make cancellation and timeouts safe.
- Measure memory, wall-clock time, and throughput on named fixtures.
- Include worst-case and adversarial input tests.
- Never trade structural safety for speed without explicit configuration and evidence.

Report benchmark hardware, software versions, corpus composition, and measurement method.

## 23. Test strategy

### Unit tests

- Each rule operation and boundary condition.
- Rule schema validation and deterministic ordering.
- Protected-span detection, overlap resolution, and restoration.
- Offset handling for Unicode and line endings.
- Citation formatting and escaping.
- Typed errors and resource limits.

### Property-based tests

Useful properties include:

- No-op mode returns the original content exactly.
- Protected spans remain byte-for-byte equal after restoration.
- Applying no enabled rules yields unchanged text.
- Rule ordering is deterministic.
- Invalid rule data never executes arbitrary code.
- Serialization/reopening preserves supported document structure.

### Golden tests

Maintain versioned input/output fixtures for representative text and documents. Golden changes require a reviewed explanation; do not update snapshots blindly to make tests pass.

### Integration tests

- Clean installation and startup.
- End-to-end text transformation and report generation.
- DOCX/LaTeX round trips.
- Citation output validation.
- Cancellation, timeout, and exception cleanup.

### Security tests

- Malformed JSON and regex patterns.
- ZIP traversal, ZIP bombs, duplicate entries, and malformed packages.
- Unicode edge cases and control characters.
- Oversized documents and pathological nesting.
- Temporary-file cleanup.
- Dependency and secret scanning.

### Evaluation tests

Use a held-out, representative corpus with human-reviewed outcomes. Report semantic errors, protected-token failures, format failures, and edit acceptance rates separately. Do not report one aggregate score that hides critical failure categories.

## 24. Continuous integration and release process

A release should not be published until:

1. The source is reproducibly installable from a clean environment.
2. Static checks, type checks, unit tests, integration tests, and security tests pass.
3. Supported-format fixtures pass round-trip checks.
4. Rule packs validate and have versioned hashes.
5. The change log and known limitations are updated.
6. No critical/high security issue remains unresolved.
7. Test reports and build artifacts are retained without retaining user document contents.
8. The release version maps unambiguously to source revision, dependency lockfile, and rule-pack versions.

Suggested CI sequence:

```text
format/lint
  -> type check
  -> unit tests
  -> property tests
  -> integration tests
  -> format round-trip tests
  -> security tests
  -> build artifact
  -> smoke test
  -> publish
```

## 25. Acceptance criteria

The core engine is acceptable for a limited release only when all applicable criteria pass:

- Deterministic output for fixed input and versions.
- Original input is never overwritten.
- Every applied edit is visible in the change report.
- Protected spans are preserved exactly or the operation is rejected.
- Invalid rule packs fail with actionable diagnostics.
- Unsupported structures are explicitly reported.
- DOCX/LaTeX outputs pass the declared compatibility tests.
- Supported code-comment edits pass parser and behavior checks.
- Citation formatting never invents metadata.
- Privacy and retention statements match the deployed data flow.
- Metrics are labelled accurately and are not presented as proof of authorship.
- Known limitations and supported versions are documented.

## 26. Operational configuration

Use configuration for limits and policies; do not hard-code environment-specific secrets.

Example:

```yaml
engine:
  version: "1.0.0"
  default_mode: "conservative"
  max_changes: 500
  fail_on_protected_span_mismatch: true
  require_review_for_semantic_edits: true

limits:
  max_input_bytes: 5000000
  max_archive_entries: 500
  max_decompressed_bytes: 25000000
  max_nesting_depth: 20

privacy:
  log_document_content: false
  retain_uploaded_files: false
  external_processing_enabled: false
```

These are starting values, not universal safe limits. Tune them through load and security testing. Validate configuration at startup and reject invalid settings.

## 27. Implementation order

1. Establish a runnable source tree, dependency lockfile, and clean startup.
2. Implement typed data models, errors, and plain-text no-op mode.
3. Implement rule schema, loader, registry, and deterministic planner.
4. Add protected-span registry and exact-restoration tests.
5. Add a small set of conservative transformations with reviewable diffs.
6. Implement structural and factual safeguards.
7. Add DOCX adapter and round-trip fixtures.
8. Add LaTeX adapter and compile fixtures.
9. Add citation formatting and separate source-verification statuses.
10. Add descriptive text metrics with precise labels.
11. Add file security limits, privacy checks, and audit events.
12. Add CI, integration tests, benchmark protocol, and release gates.
13. Expand formats or transformations only after the existing compatibility matrix passes.

## 28. Known limitations that must remain visible

- Rule-based text edits cannot guarantee semantic equivalence for arbitrary prose.
- A protected-span system can fail if detection is incomplete; tests reduce but do not eliminate this risk.
- DOCX and LaTeX ecosystems contain structures and extensions that may not be supported.
- Code safety applies only to explicitly supported languages and versions.
- Citation metadata validation does not prove a cited source supports a claim.
- Readability and compression metrics do not establish AI authorship.
- Detector behavior is external, proprietary, and changeable; no universal evasion guarantee is promised.
- Privacy depends on the actual deployed infrastructure and its configuration.

## 29. Final engineering status

This document defines a target core engine and its verification requirements. It is not evidence that the uploaded Canopus-Humanizer archive already implements these modules.

**Current evidence-based status:** architecture specification prepared; existing core implementation not verified from the supplied archive.

**To verify an implementation:** provide the actual source tree, rule data, tests, dependency manifest/lockfile, and deployment configuration with secrets removed. Run the acceptance gates and attach reproducible logs before describing any capability as tested or production-ready.
