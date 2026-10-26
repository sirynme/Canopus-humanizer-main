"""Document protection layer for LaTeX, citations, numbers, and technical terms."""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class ConservativeProtectionLayer:
    """Shields protected text elements from modification."""

    def __init__(self, additional_protected_terms: Optional[Set[str]] = None):
        self._placeholders: List[Tuple[str, str]] = []  # (placeholder, original_text)
        self.additional_protected_terms = additional_protected_terms or set()

        # Multi-word technical terms that must never be broken by word insertions
        self.TECHNICAL_MWUS = [
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
            "ImageNet-1K"
        ]

    def _generate_placeholder(self, token_type: str, index: int) -> str:
        return f"\x00_PROT_{token_type}_{index}_\x00"

    def _extract_balanced_latex_macros(self, text: str) -> List[Tuple[int, int, str]]:
        """Parses LaTeX macros with balanced curly braces (e.g. \\frac{a}{b}, \\cite{...})."""
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
                # Check for consecutive braces (e.g. \frac{num}{den})
                while curr < n and text[curr] == "{":
                    depth = 1
                    curr += 1
                    while curr < n and depth > 0:
                        if text[curr] == "{" and (curr == 0 or text[curr - 1] != "\\"):
                            depth += 1
                        elif text[curr] == "}" and (curr == 0 or text[curr - 1] != "\\"):
                            depth -= 1
                        curr += 1

                matches.append((start_pos, curr, text[start_pos:curr]))
                i = curr
            else:
                i = m.end()

        return matches

    def protect(self, text: str) -> Tuple[str, int]:
        """Shields all sensitive academic, mathematical, numerical, and citation tokens."""
        if not text or not text.strip():
            return text, 0

        self._placeholders = []

        def record(val: str, ptype: str) -> str:
            idx = len(self._placeholders)
            placeholder = self._generate_placeholder(ptype, idx)
            self._placeholders.append((placeholder, val))
            return placeholder

        # ----------------------------------------------------------------------
        # TIER 1: LaTeX Environments & Display/Inline Math
        # ----------------------------------------------------------------------
        # 1.1 LaTeX Environments: \begin{...} ... \end{...}
        def repl_env(m): return record(m.group(0), "ENV")
        text = re.sub(r"\\begin\{[a-zA-Z*]+\}[\s\S]*?\\end\{[a-zA-Z*]+\}", repl_env, text)

        # 1.2 Display Math: $$ ... $$ and \[ ... \]
        def repl_disp(m): return record(m.group(0), "DISP")
        text = re.sub(r"\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]", repl_disp, text)

        # 1.3 Inline Math: \( ... \) and $ ... $ (strictly excluding currency like $25.00 or $4.5 million)
        def repl_inline(m): return record(m.group(0), "INL")
        text = re.sub(r"\\\([\s\S]*?\\\)", repl_inline, text)
        # Inline math with dollar signs ($f(x)$)
        text = re.sub(r"(?<!\\)\$(?!\s|\d)(?:[^\$\n\\]|\\.)+?(?<!\s)\$", repl_inline, text)

        # 1.4 Balanced LaTeX Macros (\frac{...}{...}, \mathbf{...}, \cite{...})
        macro_matches = self._extract_balanced_latex_macros(text)
        for s, e, raw_macro in reversed(macro_matches):
            pl = record(raw_macro, "MACRO")
            text = text[:s] + pl + text[e:]

        # 1.5 Standalone LaTeX Commands: \ref{...}, \label{...}, \alpha, \beta, \infty
        def repl_cmd(m): return record(m.group(0), "CMD")
        text = re.sub(r"\\[a-zA-Z]+(?:\*|\b)", repl_cmd, text)

        # ----------------------------------------------------------------------
        # TIER 2: Academic In-Text Citations (IEEE, APA)
        # ----------------------------------------------------------------------
        # 2.1 APA Citations: (Author et al., 2017), (Author & Author, 2020)
        def repl_apa(m): return record(m.group(0), "CIT_APA")
        text = re.sub(r"\([A-Z][a-zA-Z\s&]+(?:et\s+al\.)?,\s*\d{4}[a-z]?(?:;\s*[A-Z][a-zA-Z\s&]+(?:et\s+al\.)?,\s*\d{4}[a-z]?)*\)", repl_apa, text)

        # 2.2 IEEE Citations: [1], [1, 2], [1-3]
        def repl_ieee(m): return record(m.group(0), "CIT_IEEE")
        text = re.sub(r"\[\d+(?:[,\-–]\s*\d+)*\]", repl_ieee, text)

        # ----------------------------------------------------------------------
        # TIER 3: Research Proposal Structural Headings & Variables
        # ----------------------------------------------------------------------
        def repl_hdr(m): return record(m.group(0), "HDR")
        text = re.sub(r"(?:\b\d+\.\s+[A-Za-z\s&]+:|\bRQ\d+:|\bH[01]:)", repl_hdr, text)

        # ----------------------------------------------------------------------
        # TIER 4: Statistical Values & Confidence Intervals
        # ----------------------------------------------------------------------
        def repl_stat(m): return record(m.group(0), "STAT")
        text = re.sub(r"\b[ptFz]\s*[<>=≤≥]\s*\d+(?:\.\d+)?|\b\d+%\s*confidence\s*interval\b|\b\d+%\s*CI\b", repl_stat, text, flags=re.IGNORECASE)

        # ----------------------------------------------------------------------
        # TIER 5: Multi-Word Technical Units (MWUs)
        # ----------------------------------------------------------------------
        combined_mwus = sorted(list(set(self.TECHNICAL_MWUS) | self.additional_protected_terms), key=len, reverse=True)
        for mwu in combined_mwus:
            if re.search(rf"\b{re.escape(mwu)}\b", text, flags=re.IGNORECASE):
                def repl_mwu(m): return record(m.group(0), "MWU")
                text = re.sub(rf"\b{re.escape(mwu)}\b", repl_mwu, text, flags=re.IGNORECASE)

        # ----------------------------------------------------------------------
        # TIER 6: Quantities, Currencies, Percentages & Physical Units
        # ----------------------------------------------------------------------
        # 6.1 Currencies ($4.5 million, $25.00)
        def repl_curr(m): return record(m.group(0), "CURR")
        text = re.sub(r"\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:billion|million|trillion))?\b", repl_curr, text, flags=re.IGNORECASE)

        # 6.2 Percentages (14.8%, 99.99%)
        def repl_pct(m): return record(m.group(0), "PCT")
        text = re.sub(r"\b\d+(?:\.\d+)?%", repl_pct, text)

        # 6.3 Quantities with explicit scientific/physical units
        def repl_unit(m): return record(m.group(0), "UNIT")
        unit_pattern = (
            r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*"
            r"(?:base\s+pairs|chromosome\s+pairs|parts\s+per\s+million|ppm|"
            r"meters\s+per\s+second|queries\s+per\s+second|qps|"
            r"ms|milliseconds|seconds|minutes|hours|days|weeks|months|years|"
            r"mg/kg|mg|kg|km|GB|MB|KB|GHz|MHz|°C|basis\s+points)\b"
        )
        text = re.sub(unit_pattern, repl_unit, text, flags=re.IGNORECASE)

        # 6.4 Four-digit calendar years (e.g. 1971, 2008, 2024)
        def repl_year(m): return record(m.group(0), "YEAR")
        text = re.sub(r"\b(?:19|20)\d{2}\b", repl_year, text)

        return text, len(self._placeholders)

    def restore(self, text: str, original_raw_text: str) -> Tuple[str, bool]:
        """Restores all protected tokens with fail-closed integrity validation using exact string replacement."""
        restored = text
        missing_tokens = []

        # Restore in exact reverse order using str.replace to prevent re.sub escape errors
        for placeholder, orig_val in reversed(self._placeholders):
            if placeholder in restored:
                restored = restored.replace(placeholder, orig_val, 1)
            else:
                missing_tokens.append(orig_val)

        # Clean any remaining rogue zero-byte tokens
        if "\x00" in restored:
            missing_tokens.append("Unrestored zero-byte token detected")

        # Fail-closed validation: if placeholders were dropped or damaged, roll back safely
        if missing_tokens:
            return original_raw_text, False

        return restored, True
