import pytest
from pathlib import Path

from hwp_hwpx_parser import (
    Reader,
    HWP5Reader,
    HWPXReader,
    ExtractOptions,
    TableStyle,
    read,
    extract_hwp5,
    extract_hwpx,
)


TESTS_DATA_DIR = Path(__file__).parent / "data"


class TestReader:
    def test_reader_hwp5(self):
        hwp_file = TESTS_DATA_DIR / "각주미주.hwp"
        if not hwp_file.exists():
            pytest.skip("Test file not available")

        with Reader(str(hwp_file)) as r:
            assert r.text is not None
            assert len(r.text) > 0

    @pytest.mark.skipif(
        not (Path(__file__).parent / "data" / "sample_notes.hwpx").exists(),
        reason="HWPX test file not available",
    )
    def test_reader_hwpx(self):
        hwpx_file = TESTS_DATA_DIR / "sample_notes.hwpx"
        with Reader(str(hwpx_file)) as r:
            assert r.text is not None
            assert len(r.text) > 0


class TestExtractFunctions:
    def test_extract_hwp5(self):
        hwp_file = TESTS_DATA_DIR / "각주미주.hwp"
        if not hwp_file.exists():
            pytest.skip("Test file not available")

        text, error = extract_hwp5(str(hwp_file))
        assert error is None
        assert text is not None
        assert len(text) > 0

    def test_read_function(self):
        hwp_file = TESTS_DATA_DIR / "각주미주.hwp"
        if not hwp_file.exists():
            pytest.skip("Test file not available")

        with read(str(hwp_file)) as r:
            assert r.text is not None
            assert len(r.text) > 0


class TestImports:
    def test_all_exports(self):
        from hwp_hwpx_parser import (
            ExtractOptions,
            TableData,
            TableStyle,
            ImageMarkerStyle,
            NoteData,
            HyperlinkData,
            MemoData,
            ExtractResult,
            HWP5Reader,
            HWPXReader,
            Reader,
            FileType,
            extract_hwp5,
            extract_hwpx,
            read,
        )

        assert Reader is not None
        assert HWP5Reader is not None
        assert HWPXReader is not None
