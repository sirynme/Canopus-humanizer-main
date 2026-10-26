"""Protected span detection, collision-resistant masking, and exact restoration."""

import re
import uuid
from typing import Dict, List, Optional, Sequence, Set, Tuple

from canopus_humanizer.engine.errors import ProtectionError, PLACEHOLDER_CORRUPTED, PROTECTED_SPAN_MISMATCH
from canopus_humanizer.engine.models import Change, ProtectedSpan


DEFAULT_TECHNICAL_TERMS = {
    "learning rate",
    "gradient descent",
    "convolutional kernel",
    "distributed consensus",
    "database sharding",
    "CAP theorem",
    "operating system",
    "neural network",
    "neural networks",
    "deep learning",
    "cross-validation",
    "support vector machine",
    "random forest",
    "transformer model",
    "transformer models",
    "self-attention",
    "backpropagation",
    "stochastic gradient descent",
    "representation drift",
    "catastrophic forgetting",
    "parameter isolation",
    "monoclonal antibody",
    "ribosomal transcription",
    "clinical genomics",
    "epigenetic factors",
    "longitudinal cohorts",
    "carbon sequestration",
    "albedo effect",
    "trophic cascade",
    "marginal propensity to consume",
    "capital adequacy ratio",
    "macroeconomic equilibrium",
    "liquidity trap",
    "ResNet-50",
    "Vision Transformer",
    "ImageNet-1K",
    "multi-head attention",
    "feedforward network",
    "loss function",
    "cross-entropy",
    "hyperparameter tuning",
    "overfitting",
    "underfitting",
    "regularization",
    "batch normalization",
    "layer normalization",
    "latent space",
    "vector representation",
    "embedding dimension",
    "eigenvalue",
    "eigenvalues",
    "eigenvector",
    "eigenvectors",
    "singular value decomposition",
    "principal component analysis",
    "markov decision process",
    "reinforcement learning",
    "natural language processing",
    "computer vision",
    "receiver operating characteristic",
    "area under the curve",
}


class ProtectedSpanDetector:
    """Detects immutable spans across academic, mathematical, technical, and citation domains."""

    def __init__(self, custom_terms: Optional[Sequence[str]] = None):
        self.custom_terms = set(custom_terms or [])
        self.all_terms = sorted(
            list(DEFAULT_TECHNICAL_TERMS | self.custom_terms),
            key=len,
            reverse=True,
        )

    def _extract_balanced_latex_macros(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Finds LaTeX macros with balanced curly braces (e.g. \\frac{a}{b}, \\cite{k})."""
        matches = []
        i = 0
        n = len(text)
        macro_start_re = re.compile(r"\\[a-zA-Z]+\*?(?:\[.*?\])?\{")

        while i < n:
            m = macro_start_re.search(text, i)
            if not m:
                break

            start_pos = m.start()
            brace_start = m.end() - 1
            depth = 1
            curr = brace_start + 1
            while curr < n and depth > 0:
                if text[curr] == "{" and (curr == 0 or text[curr - 1] != "\\"):
                    depth += 1
                elif text[curr] == "}" and (curr == 0 or text[curr - 1] != "\\"):
                    depth -= 1
                curr += 1

            if depth == 0:
                # Check for consecutive braced arguments (e.g. \frac{a}{b})
                while curr < n and text[curr] == "{":
                    depth = 1
                    curr += 1
                    while curr < n and depth > 0:
                        if text[curr] == "{" and (curr == 0 or text[curr - 1] != "\\"):
                            depth += 1
                        elif text[curr] == "}" and (curr == 0 or text[curr - 1] != "\\"):
                            depth -= 1
                        curr += 1

                matches.append((start_pos, curr, text[start_pos:curr], "latex_macro"))
                i = curr
            else:
                i = m.end()

        return matches

    def detect(self, text: str) -> List[ProtectedSpan]:
        """Detects all candidate protected spans in the text."""
        if not text:
            return []

        candidates: List[Tuple[int, int, str, str, str, float]] = []
        # format: (start, end, original, kind, detector, confidence)

        # 1. Code blocks (Markdown fenced blocks ```...``` and inline `...`)
        code_pattern = r"(?<!`)(?:```[\s\S]*?```|`(?![`\n])[^`\n]+`)"
        for m in re.finditer(code_pattern, text):
            match_str = m.group(0)
            kind = "code_block" if match_str.startswith("```") else "code_inline"
            candidates.append((m.start(), m.end(), match_str, kind, kind, 1.0))

        # 2. LaTeX Environments: \begin{...}...\end{...}
        for m in re.finditer(r"\\begin\{[a-zA-Z*]+\}[\s\S]*?\\end\{[a-zA-Z*]+\}", text):
            candidates.append((m.start(), m.end(), m.group(0), "latex_env", "latex_env", 1.0))

        # 3. Display Math: $$...$$ and \[...\]
        for m in re.finditer(r"\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]", text):
            candidates.append((m.start(), m.end(), m.group(0), "math_display", "latex_display_math", 1.0))

        # 4. Inline Math: \(...\) and $...$ (strictly excluding currency like $25.00)
        for m in re.finditer(r"\\\([\s\S]*?\\\)", text):
            candidates.append((m.start(), m.end(), m.group(0), "math_inline", "latex_inline_math", 1.0))
        for m in re.finditer(r"(?<!\\)\$(?!\s|\d)(?:[^\$\n\\]|\\.)+?(?<!\s)\$", text):
            candidates.append((m.start(), m.end(), m.group(0), "math_inline", "dollar_math", 1.0))

        # 5. Balanced LaTeX macros
        for s, e, orig, kind in self._extract_balanced_latex_macros(text):
            candidates.append((s, e, orig, kind, "balanced_macro_parser", 1.0))

        # 6. Standalone LaTeX commands: \alpha, \beta, \infty, etc.
        for m in re.finditer(r"\\[a-zA-Z]+(?:\*|\b)", text):
            candidates.append((m.start(), m.end(), m.group(0), "latex_cmd", "latex_cmd", 0.9))

        # 7. Citations:
        # APA: (Author et al., 2024), (Author & Author, 2020)
        apa_pattern = r"\([A-Z][a-zA-Z\s&]+(?:et\s+al\.)?,\s*\d{4}[a-z]?(?:;\s*[A-Z][a-zA-Z\s&]+(?:et\s+al\.)?,\s*\d{4}[a-z]?)*\)"
        for m in re.finditer(apa_pattern, text):
            candidates.append((m.start(), m.end(), m.group(0), "citation_apa", "citation_apa", 1.0))

        # IEEE: [1], [1, 2], [1-3]
        for m in re.finditer(r"\[\d+(?:[,\-–]\s*\d+)*\]", text):
            candidates.append((m.start(), m.end(), m.group(0), "citation_ieee", "citation_ieee", 1.0))

        # 8. Exact Quoted Passages: "..." or “...” or «...»
        quote_pattern = r'"[^"\n]{2,}"|“[^”\n]{2,}”|«[^»\n]{2,}»'
        for m in re.finditer(quote_pattern, text):
            candidates.append((m.start(), m.end(), m.group(0), "quote_passage", "quote_exact", 0.95))

        # 9. URLs, Email addresses, DOIs
        for m in re.finditer(r"https?://[^\s<>\"']+|ftp://[^\s<>\"']+", text):
            candidates.append((m.start(), m.end(), m.group(0), "url", "url_detector", 1.0))
        for m in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text):
            candidates.append((m.start(), m.end(), m.group(0), "email", "email_detector", 1.0))
        for m in re.finditer(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", text):
            candidates.append((m.start(), m.end(), m.group(0), "doi", "doi_detector", 1.0))

        # 10. Statistical values and confidence intervals: p < 0.05, 95% CI
        stat_pattern = r"\b[ptFzr]\s*[<>=≤≥]\s*\d+(?:\.\d+)?|\b\d+%\s*confidence\s*interval\b|\b\d+%\s*CI\b"
        for m in re.finditer(stat_pattern, text, flags=re.IGNORECASE):
            candidates.append((m.start(), m.end(), m.group(0), "statistic", "stat_detector", 1.0))

        # 11. Currencies: $25.00, $4.5 million, €100, £50
        curr_pattern = r"(?:[\$€£¥])\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:billion|million|trillion))?\b"
        for m in re.finditer(curr_pattern, text, flags=re.IGNORECASE):
            candidates.append((m.start(), m.end(), m.group(0), "currency", "currency_detector", 1.0))

        # 12. Percentages: 14.8%, 99.99%
        for m in re.finditer(r"\b\d+(?:\.\d+)?%", text):
            candidates.append((m.start(), m.end(), m.group(0), "percentage", "pct_detector", 1.0))

        # 13. Quantities with scientific and physical units
        unit_pattern = (
            r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*"
            r"(?:base\s+pairs|chromosome\s+pairs|parts\s+per\s+million|ppm|"
            r"meters\s+per\s+second|queries\s+per\s+second|qps|"
            r"ms|milliseconds|seconds|minutes|hours|days|weeks|months|years|"
            r"mg/kg|mg|kg|km|GB|MB|KB|GHz|MHz|°C|basis\s+points)\b"
        )
        for m in re.finditer(unit_pattern, text, flags=re.IGNORECASE):
            candidates.append((m.start(), m.end(), m.group(0), "physical_quantity", "unit_detector", 1.0))

        # 14. Four-digit calendar years
        for m in re.finditer(r"\b(?:19|20)\d{2}\b", text):
            candidates.append((m.start(), m.end(), m.group(0), "calendar_year", "year_detector", 0.9))

        # 15. Decimal and integer numbers (scientific notation, etc.)
        for m in re.finditer(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b", text):
            candidates.append((m.start(), m.end(), m.group(0), "number", "number_detector", 0.85))

        # 16. Technical terms and custom glossary words
        for term in self.all_terms:
            pattern = rf"\b{re.escape(term)}\b"
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                candidates.append((m.start(), m.end(), m.group(0), "technical_term", "glossary", 0.95))

        # Resolve Overlaps:
        # Precedence: longer span first (covers larger structure), then earlier start, then higher confidence
        candidates.sort(key=lambda c: (-(c[1] - c[0]), c[0], -c[5]))

        non_overlapping: List[Tuple[int, int, str, str, str, float]] = []
        for cand in candidates:
            c_start, c_end, orig, kind, detector, conf = cand
            # Check overlap with any already selected span
            overlaps = False
            for s_start, s_end, _, _, _, _ in non_overlapping:
                if not (c_end <= s_start or c_start >= s_end):
                    overlaps = True
                    break
            if not overlaps:
                non_overlapping.append(cand)

        # Sort selected spans strictly by start offset ascending
        non_overlapping.sort(key=lambda c: c[0])

        protected_spans: List[ProtectedSpan] = []
        for idx, (s, e, orig, kind, det, conf) in enumerate(non_overlapping):
            span_id = f"span_{idx:04d}"
            protected_spans.append(
                ProtectedSpan(
                    span_id=span_id,
                    start=s,
                    end=e,
                    kind=kind,
                    original=orig,
                    detector=det,
                    confidence=conf,
                )
            )

        return protected_spans


class ProtectedSpanRegistry:
    """Manages masking of protected spans with unique tokens and verifies exact restoration."""

    def __init__(self, spans: Sequence[ProtectedSpan]):
        self.spans = sorted(list(spans), key=lambda s: s.start)
        self._nonce = uuid.uuid4().hex[:8]
        # Maps placeholder -> ProtectedSpan
        self._placeholder_map: Dict[str, ProtectedSpan] = {}
        for s in self.spans:
            placeholder = f"<<CANOPUS_PROT_{s.span_id}_{self._nonce}>>"
            self._placeholder_map[placeholder] = s

    @property
    def placeholder_map(self) -> Dict[str, ProtectedSpan]:
        return self._placeholder_map

    def mask(self, text: str) -> str:
        """Replaces protected spans in text from end to beginning to preserve offsets."""
        masked = text
        for placeholder, span in sorted(
            self._placeholder_map.items(),
            key=lambda item: item[1].start,
            reverse=True,
        ):
            s, e = span.start, span.end
            # Verify slice matches expected original
            if masked[s:e] == span.original:
                masked = masked[:s] + placeholder + masked[e:]
            else:
                # Fallback to direct replacement if text already shifted
                masked = masked.replace(span.original, placeholder, 1)
        return masked

    def remap_changes_to_original(self, changes: Sequence[Change]) -> Tuple[Change, ...]:
        """Translate change offsets from the masked text back to source offsets.

        Planning runs against a masked representation whose placeholders have
        different lengths from the protected source spans.  Returning those
        masked offsets makes audit records and API consumers point at the wrong
        characters.  Changes cannot intersect placeholders, so each boundary
        can be translated using the cumulative length delta introduced by the
        spans before it.
        """
        masked_ranges: List[Tuple[int, int, ProtectedSpan]] = []
        cumulative_delta = 0
        for placeholder, span in sorted(
            self._placeholder_map.items(), key=lambda item: item[1].start
        ):
            masked_start = span.start + cumulative_delta
            masked_end = masked_start + len(placeholder)
            masked_ranges.append((masked_start, masked_end, span))
            cumulative_delta += len(placeholder) - (span.end - span.start)

        def map_offset(offset: int, is_end: bool = False) -> int:
            delta = 0
            for masked_start, masked_end, span in masked_ranges:
                if offset < masked_start:
                    return offset - delta
                if offset <= masked_end:
                    # A valid edit will not cross a placeholder.  Mapping a
                    # boundary at either edge remains well-defined as well.
                    return span.end if is_end else span.start
                delta += (masked_end - masked_start) - (span.end - span.start)
            return offset - delta

        return tuple(
            Change(
                rule_id=change.rule_id,
                start=map_offset(change.start),
                end=map_offset(change.end, is_end=True),
                before=change.before,
                after=change.after,
                category=change.category,
                requires_review=change.requires_review,
            )
            for change in changes
        )

    def restore(self, text: str, original_raw_text: str) -> Tuple[str, bool, List[str]]:
        """
        Restores protected spans with strict fail-closed verification:
        1. Checks each placeholder appears exactly once in the transformed text.
        2. Replaces placeholder with exact original bytes.
        3. Returns (restored_text, success, errors).
        """
        errors = []

        # 1. Integrity check: each placeholder must appear exactly once
        for placeholder, span in self._placeholder_map.items():
            count = text.count(placeholder)
            if count == 0:
                errors.append(f"Protected span placeholder missing: {span.span_id} ('{span.original}')")
            elif count > 1:
                errors.append(f"Protected span placeholder duplicated ({count}x): {span.span_id} ('{span.original}')")

        if errors:
            # Fail closed: return original unmodified raw text
            return original_raw_text, False, errors

        # 2. Exact replacement
        restored = text
        for placeholder, span in self._placeholder_map.items():
            restored = restored.replace(placeholder, span.original, 1)

        # 3. Check for any leftover placeholder artifacts
        leftover = re.findall(rf"<<CANOPUS_PROT_[a-zA-Z0-9_]+_{self._nonce}>>", restored)
        if leftover:
            errors.append(f"Residual placeholders detected after restoration: {leftover}")
            return original_raw_text, False, errors

        return restored, True, []
