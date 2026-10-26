# Canopus Humanizer — Known Limitations & Technical Boundaries

**Document Version:** 4.2.0  
**Date:** 26 October 2026  

---

## 1. Semantic Equivalence & Preservation Tiers

- **Four Distinct Preservation Tiers**:
  1. *Exact Protected Span Preservation (Deterministic)*: Inline LaTeX equations, citations, code tokens, URLs, percentages, and units are masked with cryptographic nonces before rewriting and restored byte-for-byte. If any nonce is missing or altered, the engine strictly fails closed.
  2. *Numeric & Negation Preservation (Token Sets)*: Numbers, currency, and explicit negation words (`not`, `never`, `cannot`, `without`, etc.) are checked via token extraction. Any dropped or added number or negation aborts the transformation.
  3. *Directional Polarity & Certainty Checks (Heuristic)*: Shifts between certainty (`must`, `proven`) and uncertainty (`may`, `plausible`) trigger validation warnings. Inversions between positive and negative findings trigger validation rejection. These checks are lexical and do not perform syntactic dependency parsing.
  4. *Whole-Text Semantic Equivalence (Not Guaranteed)*: Rule-based substitutions and lexical heuristics do not guarantee universal semantic equivalence across unreviewed, arbitrary prose. Subtle nuance, tone shifts, or idiomatic context may be affected. For high-stakes academic, legal, or clinical submissions, human review of the generated diff remains mandatory.

- **Benchmark Exact-String Matching Limitations**:
  Reported benchmark preservation (100.0%) and error resolution (100.0%) reflect performance on the documented 10-sample evaluation corpus (`tests/benchmark/benchmark_samples.json`). The benchmark checks exact literal target strings (e.g. `Prior investigations have shown`). Valid alternative rewrites (e.g. `Previous studies indicate`) are scored as 0% by exact-string matching, which undercounts legitimate stylistic variety. These scores demonstrate engine fidelity to configured rulesets, not universal perfection across arbitrary documents.

## 2. Protected Span Incompleteness Risk

- **Domain-Specific or Unregistered Jargon**:  
  The engine includes an extensive dictionary of scientific, mathematical, and multi-word technical units (MWUs). However, novel terminology, internal project acronyms, or non-standard notation not covered by standard parsers may not be automatically protected unless supplied via `custom_protected_terms`.
- **Syntax and Delimiter Sensitivity**:  
  Non-standard LaTeX math notation (e.g., custom delimiter macros without standard `$...$` or `\[...\]`) or malformed citation brackets may bypass protected span masking. Authors should ensure valid LaTeX or standard citation syntax.

## 3. Format Adapter Boundaries

- **LaTeX Complex Macro & Package Support**:  
  The LaTeX adapter shields standard environments, math delimiters, balanced macros (`\cite`, `\ref`, `\frac`), and comments. It cannot fully parse arbitrary Turing-complete TeX macro expansions, custom catcode reassignments, or external literate programming tools (`pgfplots`, `tikz` embedded scripting).
- **Word (.docx) Formatting Granularity**:  
  DOCX paragraph rewriting preserves block formatting and primary run styles (bold/italic). Highly fragmented runs (where individual syllables of a single word have alternating font sizes or colors) will be consolidated to the dominant paragraph style upon modification.
- **Source Code Comments**:  
  The code comment adapter supports Python, C, C++, Java, JavaScript, TypeScript, and Go. It does not parse templating engines (e.g., Jinja2, JSX embedded expressions, macro-preprocessed C code) where comments and code boundaries are ambiguous.

## 4. Citation & Provenance Limitations

- **Syntactic Formatting vs. Fact Verification**:  
  The citation module strictly formats provided reference metadata and validates identifier syntax (e.g., DOI format). It operates offline by default and does not verify whether an external paper exists on CrossRef/PubMed or whether the cited paper actually supports the author's statement.
- **Zero Fabrication**:  
  The engine will never invent references or author lists. If metadata is missing or partial, the output reflects only the provided input.

## 5. Metrics & Authorship Disclaimers

- **Compression Ratio, Entropy, and Readability Are Not Proof of Authorship**:  
  Descriptive measurements (zlib compression ratio, character Shannon entropy, Flesch Reading Ease, burstiness variance) quantify surface information density. They must never be interpreted as definitive proof of AI generation, human authorship, or academic misconduct.
- **Strict Prohibition of Detector Evasion Claims**:  
  Canopus Humanizer is an academic editing and stylistic refinement engine. It does not optimize transformations to manipulate commercial plagiarism or AI-writing detector scores, nor does it guarantee or claim that outputs are "undetectable." Detector scores are unstable, non-reproducible, and irrelevant to writing quality.

## 6. Operational & Environmental Boundaries

- **Memory Limits on Extreme Inputs**:  
  Default resource limits cap uploads at 5MB raw text and 25MB decompressed archives. Larger enterprise document batches require streaming or batch chunking.
- **Type-Hint Reflection Compatibility**:  
  Runtime reflection via `typing.get_type_hints` requires explicit typing imports across all public classes. This was confirmed and verified in `engine/planner.py` during V4.2 audit.
- **API Error Handling & Production Readiness**:
  Structured FastAPI exception handlers map known domain exceptions (`InputError`, `RulesetError`, `ResourceLimitError`, `SecurityError`, `ValidationError`) into standardized 4xx JSON envelopes without exposing paths or stack traces. Unexpected internal exceptions remain HTTP 500 server errors. Production deployments must provide reverse-proxy TLS termination, rate limiting, and authenticated access.
- **Continuous Integration & Branch Protection Boundaries**:
  Automated tests and invariant checks execute via `.github/workflows/ci.yml`. However, GitHub branch protection cannot be enforced through repository files alone; an authorized repository owner must manually require the CI status check in GitHub repository settings.
