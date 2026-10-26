"""Document format adapters for Plain Text, DOCX, LaTeX, and Source Code Comments."""

from canopus_humanizer.adapters.base import BaseAdapter
from canopus_humanizer.adapters.plain_text import PlainTextAdapter
from canopus_humanizer.adapters.docx import DocxAdapter
from canopus_humanizer.adapters.latex import LatexAdapter
from canopus_humanizer.adapters.code_comments import CodeCommentAdapter

__all__ = [
    "BaseAdapter",
    "PlainTextAdapter",
    "DocxAdapter",
    "LatexAdapter",
    "CodeCommentAdapter",
]
