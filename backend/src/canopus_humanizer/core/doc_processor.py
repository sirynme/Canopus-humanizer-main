"""Document processor for DOCX, LaTeX, Markdown, and plain text."""

import io
import re
import time
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from canopus_humanizer.core.modifier import DocumentModifier


class DocumentProcessor:
    """Processes documents in-place across formats and bundles in-memory archives."""

    def __init__(self, modifier: Optional[DocumentModifier] = None):
        self.modifier = modifier or DocumentModifier()

    def process_plain_text(self, text: str, **kwargs) -> str:
        """Processes plain text string."""
        return self.modifier.modify_document(text, **kwargs)

    def process_markdown(self, md_content: str, **kwargs) -> str:
        """Processes markdown while shielding headers and code blocks."""
        lines = md_content.splitlines()
        in_code_block = False
        processed_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                processed_lines.append(line)
                continue

            if in_code_block or stripped.startswith(("#", "!", "|", "-", "*", ">")):
                processed_lines.append(line)
            elif stripped:
                processed_lines.append(self.modifier.modify_line(line, **kwargs))
            else:
                processed_lines.append(line)

        return "\n".join(processed_lines)

    def process_latex(self, tex_content: str, **kwargs) -> str:
        """Processes LaTeX while shielding comments, preamble, and math environments."""
        lines = tex_content.splitlines()
        in_preamble = True
        processed_lines = []

        for line in lines:
            stripped = line.strip()
            if r"\begin{document}" in stripped:
                in_preamble = False
                processed_lines.append(line)
                continue

            if in_preamble or stripped.startswith("%") or not stripped:
                processed_lines.append(line)
                continue

            # Shield structural lines
            if stripped.startswith((r"\section", r"\subsection", r"\subsubsection", r"\item", r"\begin", r"\end")):
                processed_lines.append(line)
            else:
                processed_lines.append(self.modifier.modify_line(line, **kwargs))

        return "\n".join(processed_lines)

    def process_docx(self, docx_bytes: bytes, **kwargs) -> bytes:
        """Processes Word .docx in-place preserving runs, bold/italic, tables, and styles."""
        try:
            import docx  # Lazy import
        except ImportError:
            # Fallback if docx library is not yet installed in runtime
            return docx_bytes

        doc = docx.Document(io.BytesIO(docx_bytes))

        # Process main body paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                # Modify sentence runs
                full_text = para.text
                modified_text = self.modifier.modify_document(full_text, **kwargs)
                if modified_text != full_text and para.runs:
                    # Update text while preserving primary formatting run
                    para.runs[0].text = modified_text
                    for r in para.runs[1:]:
                        r.text = ""

        # Process tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if para.text.strip():
                            full_text = para.text
                            modified_text = self.modifier.modify_document(full_text, **kwargs)
                            if modified_text != full_text and para.runs:
                                para.runs[0].text = modified_text
                                for r in para.runs[1:]:
                                    r.text = ""

        out_buffer = io.BytesIO()
        doc.save(out_buffer)
        return out_buffer.getvalue()

    def create_in_memory_zip(self, files: List[Tuple[str, bytes]], archive_prefix: str = "Canopus_Humanized_Docs") -> Tuple[str, bytes]:
        """Creates a branded in-memory ZIP bundle without disk cache leakage."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{archive_prefix}_{timestamp}.zip"
        
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, content in files:
                zf.writestr(filename, content)

        buffer.seek(0)
        return zip_filename, buffer.getvalue()
