"""Abstract base contract for document format adapters."""

from abc import ABC, abstractmethod
from typing import Any, Tuple

from canopus_humanizer.engine.models import DocumentModel, TransformResult


class BaseAdapter(ABC):
    """Abstract interface all format adapters must implement."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Name of the document format (e.g. 'plain_text', 'docx', 'latex', 'code_comments')."""
        pass

    @abstractmethod
    def parse(self, raw_input: Any) -> DocumentModel:
        """Parses raw input into structured DocumentModel blocks."""
        pass

    @abstractmethod
    def transform(self, raw_input: Any, pipeline: Any, **kwargs) -> Tuple[Any, TransformResult]:
        """Transforms document through pipeline and returns (serialized_output, TransformResult)."""
        pass
