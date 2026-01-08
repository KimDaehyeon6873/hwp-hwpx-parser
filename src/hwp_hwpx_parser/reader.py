"""Unified HWP/HWPX Reader"""

from pathlib import Path
from typing import Union, Optional, List, Any
from enum import Enum, auto

from .models import ExtractOptions, TableData, ExtractResult
from .hwp5 import HWP5Reader, OLEFILE_AVAILABLE
from .hwpx import HWPXReader


class FileType(Enum):
    HWP5 = auto()
    HWPX = auto()
    UNKNOWN = auto()


class Reader:
    """
    Unified HWP/HWPX reader.

    Handles both HWP 5.0 and HWPX files with the same interface.
    Pure Python implementation, no JVM required.

    Example:
        >>> with Reader("document.hwp") as r:
        ...     print(r.text)
        ...     for table in r.tables:
        ...         print(table.to_markdown())
    """

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)
        self._reader = None
        self._file_type = self._detect_type()

    def _detect_type(self) -> FileType:
        suffix = self.filepath.suffix.lower()
        if suffix == ".hwp":
            return FileType.HWP5
        elif suffix == ".hwpx":
            return FileType.HWPX
        return FileType.UNKNOWN

    def _get_reader(self):
        if self._reader is not None:
            return self._reader

        if self._file_type == FileType.HWP5:
            if not OLEFILE_AVAILABLE:
                raise ImportError("olefile package required: pip install olefile")
            self._reader = HWP5Reader(str(self.filepath))
        elif self._file_type == FileType.HWPX:
            self._reader = HWPXReader(str(self.filepath))
        else:
            raise ValueError(f"Unsupported file format: {self.filepath.suffix}")

        return self._reader

    def __enter__(self):
        reader = self._get_reader()
        reader._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._reader is not None:
            self._reader._close()

    @property
    def file_type(self) -> FileType:
        return self._file_type

    @property
    def is_valid(self) -> bool:
        try:
            reader = self._get_reader()
            return reader.is_valid()
        except Exception:
            return False

    @property
    def is_encrypted(self) -> bool:
        try:
            reader = self._get_reader()
            return reader.is_encrypted()
        except Exception:
            return False

    def extract_text(self, options: Optional[ExtractOptions] = None) -> str:
        reader = self._get_reader()
        return reader.extract_text(options)

    def extract_text_with_notes(
        self, options: Optional[ExtractOptions] = None
    ) -> ExtractResult:
        reader = self._get_reader()
        return reader.extract_text_with_notes(options)

    @property
    def text(self) -> str:
        return self.extract_text()

    @property
    def tables(self) -> List[TableData]:
        reader = self._get_reader()
        return reader.get_tables()

    def get_tables(self, options: Optional[ExtractOptions] = None) -> List[TableData]:
        reader = self._get_reader()
        return reader.get_tables(options)

    def get_memos(self) -> List[Any]:
        reader = self._get_reader()
        return reader.get_memos()

    def find_all(self, tag: str) -> List[Any]:
        if tag == "table":
            return self.tables
        elif tag == "paragraph":
            text = self.extract_text()
            return text.split("\n\n") if text else []
        return []

    def get_tables_as_markdown(self) -> List[str]:
        return [t.to_markdown() for t in self.tables]

    def get_tables_as_csv(self, delimiter: str = ",") -> List[str]:
        return [t.to_csv(delimiter) for t in self.tables]

    def close(self):
        if self._reader is not None:
            self._reader.close()
            self._reader = None


def read(filepath: Union[str, Path]) -> Reader:
    """
    Open HWP/HWPX file and return a Reader.

    Example:
        >>> reader = read("document.hwp")
        >>> print(reader.text)
        >>> reader.close()
    """
    return Reader(filepath)
