"""
HWP/HWPX Parser Data Models

Pure Python data models for text extraction results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Literal, Tuple


class TableStyle(Enum):
    """Table output style."""

    INLINE = "inline"
    MARKDOWN = "markdown"
    CSV = "csv"


class ImageMarkerStyle(Enum):
    """Image marker style."""

    NONE = "none"
    SIMPLE = "simple"
    WITH_NAME = "with_name"


@dataclass
class ExtractOptions:
    """
    Text extraction options.

    Example:
        >>> options = ExtractOptions()
        >>> options.table_style = TableStyle.MARKDOWN
    """

    table_style: TableStyle = TableStyle.MARKDOWN
    table_delimiter: str = ","
    image_marker: ImageMarkerStyle = ImageMarkerStyle.SIMPLE
    paragraph_separator: str = "\n\n"
    line_separator: str = "\n"
    include_empty_paragraphs: bool = False


@dataclass
class TableData:
    """
    Table data model.

    Attributes:
        rows: 2D list of cell contents [[cell1, cell2], [cell3, cell4], ...]
    """

    rows: List[List[str]] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        if not self.rows:
            return ""

        lines = []
        for i, row in enumerate(self.rows):
            clean_row = [
                cell.replace("\n", " ").replace("\r", "").replace("|", "\\|").strip()
                for cell in row
            ]
            lines.append("| " + " | ".join(clean_row) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * len(clean_row)) + " |")

        return "\n".join(lines)

    def to_csv(self, delimiter: str = ",") -> str:
        """Convert to CSV format."""
        if not self.rows:
            return ""

        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output, delimiter=delimiter)

        for row in self.rows:
            clean_row = [
                cell.replace("\n", " ").replace("\r", "").strip() for cell in row
            ]
            writer.writerow(clean_row)

        return output.getvalue().strip()

    def to_inline(self) -> str:
        """Convert to inline format (all cells joined by space)."""
        if not self.rows:
            return ""

        all_cells = []
        for row in self.rows:
            for cell in row:
                clean_cell = cell.replace("\n", " ").replace("\r", "").strip()
                if clean_cell:
                    all_cells.append(clean_cell)

        return " ".join(all_cells)

    def format(self, style: TableStyle, delimiter: str = ",") -> str:
        """Format table with specified style."""
        if style == TableStyle.MARKDOWN:
            return self.to_markdown()
        elif style == TableStyle.CSV:
            return self.to_csv(delimiter)
        elif style == TableStyle.INLINE:
            return self.to_inline()
        return self.to_markdown()

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    def __repr__(self) -> str:
        return f"TableData(rows={self.row_count}, cols={self.col_count})"


@dataclass
class NoteData:
    """
    Footnote/Endnote data model.

    Attributes:
        note_type: "footnote" or "endnote"
        number: Note number (matches [^N] marker in text)
        text: Note content
    """

    note_type: Literal["footnote", "endnote"]
    number: int
    text: str

    def __repr__(self) -> str:
        type_str = "footnote" if self.note_type == "footnote" else "endnote"
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"NoteData({type_str}[{self.number}]: {preview})"


@dataclass
class HyperlinkData:
    """
    Hyperlink data model.

    Attributes:
        text: Display text
        url: Link URL
    """

    text: str
    url: str

    def __repr__(self) -> str:
        text_preview = self.text[:20] + "..." if len(self.text) > 20 else self.text
        url_preview = self.url[:30] + "..." if len(self.url) > 30 else self.url
        return f"HyperlinkData({text_preview} -> {url_preview})"


@dataclass
class MemoData:
    """
    Memo data model.

    Attributes:
        text: Memo content
        memo_id: Memo ID
        author: Author (if available)
        width: Memo width (if available)
        fill_color: Background color (if available)
    """

    text: str
    memo_id: Optional[str] = None
    author: Optional[str] = None
    width: Optional[int] = None
    fill_color: Optional[str] = None

    def __repr__(self) -> str:
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"MemoData({preview})"


@dataclass
class ExtractResult:
    """
    Text extraction result with notes and links.

    Attributes:
        text: Extracted text (footnotes marked as [^N], endnotes as [^eN])
        footnotes: List of footnotes
        endnotes: List of endnotes
        hyperlinks: List of hyperlinks (text, url) tuples
        memos: List of memos
    """

    text: str
    footnotes: List[NoteData] = field(default_factory=list)
    endnotes: List[NoteData] = field(default_factory=list)
    hyperlinks: List[Tuple[str, str]] = field(default_factory=list)
    memos: List[MemoData] = field(default_factory=list)

    @property
    def notes(self) -> List[NoteData]:
        """All notes (footnotes + endnotes)."""
        return self.footnotes + self.endnotes

    def get_note(
        self, number: int, note_type: Optional[Literal["footnote", "endnote"]] = None
    ) -> Optional[NoteData]:
        """Find note by number."""
        if note_type == "footnote" or note_type is None:
            for note in self.footnotes:
                if note.number == number:
                    return note
        if note_type == "endnote" or note_type is None:
            for note in self.endnotes:
                if note.number == number:
                    return note
        return None


def format_image_marker(
    style: ImageMarkerStyle, filename: Optional[str] = None, index: Optional[int] = None
) -> str:
    """Generate image marker string."""
    if style == ImageMarkerStyle.NONE:
        return ""
    elif style == ImageMarkerStyle.SIMPLE:
        return "[IMAGE]"
    elif style == ImageMarkerStyle.WITH_NAME:
        if filename:
            return f"[IMAGE: {filename}]"
        elif index is not None:
            return f"[IMAGE: image_{index:03d}]"
        return "[IMAGE]"
    return "[IMAGE]"
