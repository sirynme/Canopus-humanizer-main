"""LaTeX document adapter with brace-balance tracking and preamble shielding."""

import re
from typing import Any, List, Optional, Tuple, Union

from canopus_humanizer.adapters.base import BaseAdapter
from canopus_humanizer.engine.errors import FormatError, PARSER_FAILED, OUTPUT_VALIDATION_FAILED
from canopus_humanizer.engine.models import DocumentBlock, DocumentModel, TransformRequest, TransformResult, ValidationIssue


class LatexAdapter(BaseAdapter):
    """LaTeX format adapter shielding preamble, macros, math, and verifying balanced braces."""

    @property
    def format_name(self) -> str:
        return "latex"

    def _check_brace_balance(self, text: str) -> Tuple[int, int]:
        """Counts unescaped opening and closing curly braces."""
        open_braces = 0
        close_braces = 0
        n = len(text)
        for i in range(n):
            if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
                open_braces += 1
            elif text[i] == "}" and (i == 0 or text[i - 1] != "\\"):
                close_braces += 1
        return open_braces, close_braces

    def parse(self, raw_input: Union[str, bytes]) -> DocumentModel:
        """Parses LaTeX file content into structural blocks."""
        if isinstance(raw_input, bytes):
            text = raw_input.decode("utf-8", errors="replace")
        else:
            text = raw_input

        lines = text.splitlines(keepends=True)
        blocks: List[DocumentBlock] = []
        in_preamble = True
        offset = 0

        preamble_lines = []
        body_lines = []

        for line in lines:
            stripped = line.strip()
            if r"\begin{document}" in stripped:
                in_preamble = False
                preamble_lines.append(line)
                blocks.append(
                    DocumentBlock(
                        block_id="preamble",
                        block_type="preamble",
                        start=offset,
                        end=offset + len("".join(preamble_lines)),
                        content="".join(preamble_lines),
                    )
                )
                offset += len("".join(preamble_lines))
                continue

            if in_preamble:
                preamble_lines.append(line)
            else:
                body_lines.append(line)

        if body_lines:
            blocks.append(
                DocumentBlock(
                    block_id="body",
                    block_type="body",
                    start=offset,
                    end=offset + len("".join(body_lines)),
                    content="".join(body_lines),
                )
            )

        return DocumentModel(
            blocks=tuple(blocks),
            format_name=self.format_name,
            source_metadata={"has_preamble": bool(preamble_lines)},
        )

    def transform(
        self,
        raw_input: Union[str, bytes],
        pipeline: Any,
        request: Optional[TransformRequest] = None,
        **kwargs,
    ) -> Tuple[str, TransformResult]:
        """Transforms LaTeX text while shielding preamble, comments, and validating brace parity."""
        if isinstance(raw_input, bytes):
            text = raw_input.decode("utf-8", errors="replace")
        else:
            text = raw_input

        orig_open, orig_close = self._check_brace_balance(text)

        # Check for \begin{document}
        split_token = r"\begin{document}"
        if split_token in text:
            preamble, body = text.split(split_token, 1)
            preamble_part = preamble + split_token
        else:
            preamble_part = ""
            body = text

        # Delegate body transformation to pipeline
        mode = request.mode if request else kwargs.get("mode", "conservative")
        ruleset_ids = request.ruleset_ids if request else kwargs.get("ruleset_ids", ("base",))
        custom_terms = request.custom_protected_terms if request else kwargs.get("custom_protected_terms", ())
        req = TransformRequest(
            text=body,
            mode=mode,
            ruleset_ids=ruleset_ids,
            custom_protected_terms=custom_terms,
        )
        body_result = pipeline.process(req)

        transformed_full = preamble_part + body_result.transformed_text

        # Validate brace parity
        trans_open, trans_close = self._check_brace_balance(transformed_full)
        issues = list(body_result.issues)

        if (orig_open != trans_open) or (orig_close != trans_close):
            issues.append(
                ValidationIssue(
                    code="LATEX_BRACE_IMBALANCE",
                    severity="error",
                    message=(
                        f"LaTeX curly brace imbalance detected. "
                        f"Original: ({orig_open} open, {orig_close} close); "
                        f"Transformed: ({trans_open} open, {trans_close} close)."
                    ),
                )
            )
            # Fail closed: reject modification
            return text, TransformResult(
                original_text=text,
                transformed_text=text,
                changes=body_result.changes,
                issues=tuple(issues),
                engine_version=pipeline.engine_version,
                ruleset_versions=body_result.ruleset_versions,
                accepted=False,
            )

        result = TransformResult(
            original_text=text,
            transformed_text=transformed_full,
            changes=body_result.changes,
            issues=tuple(issues),
            engine_version=pipeline.engine_version,
            ruleset_versions=body_result.ruleset_versions,
            accepted=not any(i.severity == "error" for i in issues),
        )

        return transformed_full, result
