"""Citation formatters for APA, IEEE, BibTeX, and Chicago styles."""

import re
from typing import Any, Dict, List, Optional


def escape_bibtex(val: str) -> str:
    """Escapes special LaTeX / BibTeX characters in fields."""
    replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("_", r"\_"),
        ("#", r"\#"),
        ("$", r"\$"),
    ]
    res = val
    for orig, rep in replacements:
        res = res.replace(orig, rep)
    return res


class CitationFormatter:
    """Formats verified reference metadata into standard scholarly citation formats."""

    @staticmethod
    def format_apa(meta: Dict[str, Any]) -> str:
        """
        Formats APA 7th edition reference entry.
        Example: Smith, J. D., & Taylor, R. (2023). Deep neural architectures. Journal of AI, 12(3), 45-56.
        """
        authors = meta.get("authors", [])
        if isinstance(authors, str):
            authors = [authors]

        if not authors:
            author_str = "Anonymous"
        elif len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]}, & {authors[1]}"
        else:
            author_str = f"{', '.join(authors[:-1])}, & {authors[-1]}"

        year = meta.get("year", "n.d.")
        title = meta.get("title", "Untitled")
        venue = meta.get("venue") or meta.get("journal", "")
        volume = meta.get("volume", "")
        issue = meta.get("issue", "")
        pages = meta.get("pages", "")
        doi = meta.get("doi", "")

        parts = [f"{author_str} ({year}). {title}."]
        if venue:
            venue_part = venue
            if volume:
                venue_part += f", {volume}"
                if issue:
                    venue_part += f"({issue})"
            if pages:
                venue_part += f", {pages}"
            parts.append(f"{venue_part}.")

        if doi:
            doi_clean = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            parts.append(doi_clean)

        return " ".join(parts)

    @staticmethod
    def format_ieee(meta: Dict[str, Any], index: int = 1) -> str:
        """
        Formats IEEE reference entry.
        Example: [1] J. D. Smith and R. Taylor, "Deep neural architectures," Journal of AI, vol. 12, no. 3, pp. 45-56, 2023.
        """
        authors = meta.get("authors", [])
        if isinstance(authors, str):
            authors = [authors]

        if not authors:
            author_str = "Anon."
        elif len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} and {authors[1]}"
        else:
            author_str = f"{', '.join(authors[:-1])}, and {authors[-1]}"

        title = meta.get("title", "Untitled")
        venue = meta.get("venue") or meta.get("journal", "")
        volume = meta.get("volume", "")
        issue = meta.get("issue", "")
        pages = meta.get("pages", "")
        year = meta.get("year", "n.d.")

        elements = [f"[{index}] {author_str}, \"{title},\""]
        if venue:
            elements.append(f"{venue},")
        if volume:
            elements.append(f"vol. {volume},")
        if issue:
            elements.append(f"no. {issue},")
        if pages:
            elements.append(f"pp. {pages},")
        elements.append(f"{year}.")

        return " ".join(elements)

    @staticmethod
    def format_bibtex(meta: Dict[str, Any], entry_type: str = "article") -> str:
        """
        Formats BibTeX entry with proper character escaping.
        """
        key = meta.get("key") or meta.get("id")
        if not key:
            authors = meta.get("authors", [])
            first_author = authors[0].split()[-1] if authors else "ref"
            year = meta.get("year", "0000")
            key = f"{first_author.lower()}{year}"

        authors = meta.get("authors", [])
        if isinstance(authors, list):
            author_val = " and ".join(authors)
        else:
            author_val = str(authors)

        fields = [
            f"  author    = {{{escape_bibtex(author_val)}}}",
            f"  title     = {{{escape_bibtex(meta.get('title', ''))}}}",
        ]

        if "journal" in meta or "venue" in meta:
            fields.append(f"  journal   = {{{escape_bibtex(meta.get('journal') or meta.get('venue', ''))}}}")
        if "year" in meta:
            fields.append(f"  year      = {{{meta['year']}}}")
        if "volume" in meta:
            fields.append(f"  volume    = {{{meta['volume']}}}")
        if "number" in meta or "issue" in meta:
            fields.append(f"  number    = {{{meta.get('number') or meta.get('issue')}}}")
        if "pages" in meta:
            fields.append(f"  pages     = {{{meta['pages']}}}")
        if "doi" in meta:
            fields.append(f"  doi       = {{{meta['doi']}}}")

        body = ",\n".join(fields)
        return f"@{entry_type}{{{key},\n{body}\n}}"
