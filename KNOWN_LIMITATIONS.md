# Canopus Humanizer — Known Limitations & Technical Boundaries

**Document Version:** 4.2.0  
**Date:** 26 October 2026  

---

## 1. Semantic Equivalence Boundaries

- **Rule-Based Heuristics Do Not Guarantee Universal Semantic Equivalence**:  
  While the engine enforces strict negation, modal qualification, and numeric preservation gates, rule-driven phrase replacements can produce subtle tone or register shifts depending on context. For high-stakes legal, medical, or doctoral submissions, human review of the generated diff remains essential.
- **Evaluation Corpus Scope**:  
  Reported benchmark preservation (100.0%) and error resolution (100.0%) reflect performance on the documented 10-sample evaluation corpus (`tests/benchmark/benchmark_samples.json`) and invariant test suites. These results demonstrate engine correctness on tested patterns but do not constitute an unconstrained universal guarantee for arbitrary, unreviewed prose.

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
- **Infrastructure Security**:  
  While the core engine performs all transformations in memory and never retains uploaded files, overall privacy depends on the host operating system, TLS termination, and reverse-proxy logging configuration in production deployments.
