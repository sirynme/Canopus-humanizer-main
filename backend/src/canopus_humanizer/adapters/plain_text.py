"""Plain-text format adapter."""

from typing import Any, Optional, Tuple, Union

from canopus_humanizer.adapters.base import BaseAdapter
from canopus_humanizer.engine.errors import InputError, NUL_BYTE_DETECTED
from canopus_humanizer.engine.models import DocumentBlock, DocumentModel, TransformRequest, TransformResult


class PlainTextAdapter(BaseAdapter):
    """Reference plain-text adapter supporting UTF-8, no-op validation, and offset mapping."""

    @property
    def format_name(self) -> str:
        return "plain_text"

    def parse(self, raw_input: Union[str, bytes]) -> DocumentModel:
        """Parses plain text, validating UTF-8 encoding and detecting illegal NUL bytes."""
        if isinstance(raw_input, bytes):
            try:
                text = raw_input.decode("utf-8")
            except UnicodeDecodeError as e:
                raise InputError(f"Input is not valid UTF-8 text: {e}", code="ENCODING_ERROR")
        elif isinstance(raw_input, str):
            text = raw_input
        else:
            raise InputError(f"Expected str or bytes, got {type(raw_input).__name__}", code="INPUT_INVALID")

        if "\x00" in text:
            raise InputError("Plain text input contains prohibited NUL bytes", code=NUL_BYTE_DETECTED)

        # Standardize line breaks: keep track of original
        blocks = []
        raw_paragraphs = text.split("\n\n")
        curr_offset = 0

        for idx, p in enumerate(raw_paragraphs):
            p_len = len(p)
            blocks.append(
                DocumentBlock(
                    block_id=f"para_{idx:04d}",
                    block_type="paragraph",
                    start=curr_offset,
                    end=curr_offset + p_len,
                    content=p,
                )
            )
            curr_offset += p_len + 2  # account for \n\n

        return DocumentModel(
            blocks=tuple(blocks),
            format_name=self.format_name,
            source_metadata={"total_length": len(text), "block_count": len(blocks)},
        )

    def transform(
        self,
        raw_input: Union[str, bytes],
        pipeline: Any,
        request: Optional[TransformRequest] = None,
        no_op: bool = False,
        **kwargs,
    ) -> Tuple[str, TransformResult]:
        """Transforms plain text via pipeline."""
        doc_model = self.parse(raw_input)
        full_text = "\n\n".join(b.content for b in doc_model.blocks)

        req = request or TransformRequest(text=full_text, **kwargs)

        if no_op:
            # No-op pass: returns exact original text with empty changes
            result = pipeline.process(req, no_op=True)
            return full_text, result

        result = pipeline.process(req)
        return result.transformed_text, result
