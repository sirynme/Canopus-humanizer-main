"""Language-aware source-code comment adapter preserving non-comment code byte-for-byte."""

import re
from typing import Any, List, Optional, Tuple, Union

from canopus_humanizer.adapters.base import BaseAdapter
from canopus_humanizer.engine.errors import FormatError
from canopus_humanizer.engine.models import DocumentBlock, DocumentModel, TransformRequest, TransformResult, ValidationIssue


class CodeCommentAdapter(BaseAdapter):
    """
    Extracts and transforms ONLY comment text in source files.
    Guarantees non-comment code tokens remain 100% byte-for-byte identical.
    Supported languages: python, c, cpp, java, javascript, typescript, go.
    """

    SUPPORTED_LANGUAGES = {"python", "py", "c", "cpp", "java", "javascript", "js", "typescript", "ts", "go"}

    @property
    def format_name(self) -> str:
        return "code_comments"

    def _extract_python_comments(self, code: str) -> List[Tuple[int, int, str]]:
        """Extracts python line comments while ignoring '#' inside quoted strings."""
        comments = []
        lines = code.splitlines(keepends=True)
        curr_offset = 0

        for line in lines:
            in_single_quote = False
            in_double_quote = False
            escaped = False
            comment_start = -1

            for i, ch in enumerate(line):
                if escaped:
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue

                if ch == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote
                elif ch == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif ch == "#" and not in_single_quote and not in_double_quote:
                    comment_start = i
                    break

            if comment_start != -1:
                # Store start and end offsets of comment (excluding the '#' marker itself)
                c_content = line[comment_start + 1:].rstrip("\r\n")
                abs_s = curr_offset + comment_start + 1
                abs_e = abs_s + len(c_content)
                comments.append((abs_s, abs_e, c_content))

            curr_offset += len(line)

        return comments

    def _extract_c_style_comments(self, code: str) -> List[Tuple[int, int, str]]:
        """Extracts // and /* ... */ comments while ignoring comment tokens inside strings."""
        comments = []
        n = len(code)
        i = 0
        in_string = False
        string_char = ""
        escaped = False

        while i < n:
            ch = code[i]
            if escaped:
                escaped = False
                i += 1
                continue

            if ch == "\\":
                escaped = True
                i += 1
                continue

            if in_string:
                if ch == string_char:
                    in_string = False
                i += 1
                continue

            if ch in ("'", '"'):
                in_string = True
                string_char = ch
                i += 1
                continue

            # Check for line comment //
            if ch == "/" and i + 1 < n and code[i + 1] == "/":
                start_c = i + 2
                end_c = start_c
                while end_c < n and code[end_c] not in ("\r", "\n"):
                    end_c += 1
                comments.append((start_c, end_c, code[start_c:end_c]))
                i = end_c
                continue

            # Check for block comment /* ... */
            if ch == "/" and i + 1 < n and code[i + 1] == "*":
                start_c = i + 2
                end_c = code.find("*/", start_c)
                if end_c == -1:
                    end_c = n
                comments.append((start_c, end_c, code[start_c:end_c]))
                i = end_c + 2
                continue

            i += 1

        return comments

    def parse(self, raw_input: Union[str, bytes], language: str = "python") -> DocumentModel:
        """Parses comments from source file."""
        text = raw_input.decode("utf-8", errors="replace") if isinstance(raw_input, bytes) else raw_input
        lang = language.lower()

        if lang in ("python", "py"):
            comments = self._extract_python_comments(text)
        elif lang in ("c", "cpp", "java", "javascript", "js", "typescript", "ts", "go"):
            comments = self._extract_c_style_comments(text)
        else:
            raise FormatError(f"Unsupported language '{language}' for comment adapter", code="UNSUPPORTED_LANGUAGE")

        blocks = [
            DocumentBlock(
                block_id=f"comment_{idx:04d}",
                block_type="comment",
                start=s,
                end=e,
                content=txt,
            )
            for idx, (s, e, txt) in enumerate(comments)
        ]

        return DocumentModel(
            blocks=tuple(blocks),
            format_name=self.format_name,
            source_metadata={"language": lang, "comment_count": len(blocks)},
        )

    def transform(
        self,
        raw_input: Union[str, bytes],
        pipeline: Any,
        language: str = "python",
        request: Optional[TransformRequest] = None,
        **kwargs,
    ) -> Tuple[str, TransformResult]:
        """Transforms source code comments and rigorously verifies non-comment code equality."""
        text = raw_input.decode("utf-8", errors="replace") if isinstance(raw_input, bytes) else raw_input
        doc_model = self.parse(text, language=language)

        all_changes = []
        all_issues = []
        transformed_code = text

        # Transform comments in reverse order so character offsets do not drift
        for block in sorted(doc_model.blocks, key=lambda b: b.start, reverse=True):
            raw_comment = block.content
            if not raw_comment.strip():
                continue

            req = TransformRequest(
                text=raw_comment,
                mode=request.mode if request else "conservative",
                ruleset_ids=request.ruleset_ids if request else ("base",),
            )
            res = pipeline.process(req)
            all_changes.extend(res.changes)
            all_issues.extend(res.issues)

            if res.transformed_text != raw_comment:
                s, e = block.start, block.end
                transformed_code = transformed_code[:s] + res.transformed_text + transformed_code[e:]

        # Rigorous safety check: verify code minus comments is byte-for-byte identical
        orig_non_comment = self._strip_comments(text, language)
        trans_non_comment = self._strip_comments(transformed_code, language)

        if orig_non_comment != trans_non_comment:
            all_issues.append(
                ValidationIssue(
                    code="CODE_CORRUPTED",
                    severity="error",
                    message="Fatal error: Non-comment source code was corrupted during comment transformation.",
                )
            )
            # Fail closed: restore original code
            return text, TransformResult(
                original_text=text,
                transformed_text=text,
                changes=tuple(all_changes),
                issues=tuple(all_issues),
                engine_version=pipeline.engine_version,
                ruleset_versions=pipeline.registry.get_version_info(
                    request.ruleset_ids if request else ("base",)
                ),
                accepted=False,
            )

        result = TransformResult(
            original_text=text,
            transformed_text=transformed_code,
            changes=tuple(all_changes),
            issues=tuple(all_issues),
            engine_version=pipeline.engine_version,
            ruleset_versions=pipeline.registry.get_version_info(
                request.ruleset_ids if request else ("base",)
            ),
            accepted=not any(i.severity == "error" for i in all_issues),
        )

        return transformed_code, result

    def _strip_comments(self, code: str, language: str) -> str:
        """Removes comment contents to compare underlying code syntax."""
        lang = language.lower()
        if lang in ("python", "py"):
            comments = self._extract_python_comments(code)
        else:
            comments = self._extract_c_style_comments(code)

        stripped = code
        for s, e, _ in sorted(comments, key=lambda c: c[0], reverse=True):
            stripped = stripped[:s] + stripped[e:]
        return stripped
