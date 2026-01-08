"""
HWP-HWPX Parser - 순수 Python HWP/HWPX 파서

JVM 없이 HWP/HWPX 파일에서 텍스트, 표, 각주, 미주, 메모를 추출합니다.

사용법:
    >>> from hwp_hwpx_parser import Reader
    >>> with Reader("document.hwp") as r:
    ...     print(r.text)
    ...     print(r.get_memos())

문서 편집이 필요하면 hwp-hwpx-editor를 설치하세요:
    pip install hwp-hwpx-editor
"""

__version__ = "0.1.0"

from .models import (
    ExtractOptions,
    TableData,
    TableStyle,
    ImageMarkerStyle,
    NoteData,
    HyperlinkData,
    MemoData,
    ExtractResult,
)
from .hwp5 import HWP5Reader, extract_hwp5, OLEFILE_AVAILABLE
from .hwpx import HWPXReader, extract_hwpx
from .reader import Reader, FileType, read

__all__ = [
    "ExtractOptions",
    "TableData",
    "TableStyle",
    "ImageMarkerStyle",
    "NoteData",
    "HyperlinkData",
    "MemoData",
    "ExtractResult",
    "HWP5Reader",
    "HWPXReader",
    "Reader",
    "FileType",
    "extract_hwp5",
    "extract_hwpx",
    "read",
    "OLEFILE_AVAILABLE",
]
