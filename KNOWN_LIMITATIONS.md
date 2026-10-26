# Canopus Humanizer — Known Limitations & Technical Boundaries

**Document Version:** 1.0.0  
**Date:** 26 October 2026  

---

## 1. Semantic Equivalence Boundaries

- **Rule-Based Heuristics Do Not Guarantee Universal Semantic Equivalence**:  
  While the engine enforces strict negation, modal qualification, and numeric preservation gates, rule-driven phrase replacements can produce subtle tone or register shifts depending on context. For high-stakes legal, medical, or doctoral submissions, human review of the generated diff remains essential.

## 2. Protected Span Incompleteness Risk

- **Domain-Specific or Unregistered Jargon**:  
  The engine includes an extensive dictionary of scientific, mathematical, and multi-word technical units (MWUs). However, novel terminology, internal project acronyms, or non-standard notation not covered by standard parsers may not be automatically protected unless supplied via `custom_protected_terms`.

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
- **No Detector Evasion Guarantee**:  
  Canopus Humanizer is an academic editing and stylistic refinement engine. It does not guarantee, promise, or promote evasion of commercial plagiarism or AI-writing detectors.

## 6. Operational & Environmental Boundaries

- **Memory Limits on Extreme Inputs**:  
  Default resource limits cap uploads at 5MB raw text and 25MB decompressed archives. Larger enterprise document batches require streaming or batch chunking.
- **Infrastructure Security**:  
  While the core engine performs all transformations in memory and never retains uploaded files, overall privacy depends on the host operating system, TLS termination, and reverse-proxy logging configuration in production deployments.
