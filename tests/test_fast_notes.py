"""
Fast Layer - 각주/미주/하이퍼링크 추출 테스트
"""

import pytest
from pathlib import Path

from hwp_hwpx_parser import (
    HWP5Reader,
    HWPXReader,
    ExtractOptions,
    NoteData,
    ExtractResult,
)


TESTS_DATA_DIR = Path(__file__).parent / "data"


class TestHWP5Notes:
    """HWP5 각주/미주 추출 테스트"""

    @pytest.fixture
    def basic_notes_file(self):
        return TESTS_DATA_DIR / "각주미주.hwp"

    @pytest.fixture
    def sample_notes_file(self):
        return TESTS_DATA_DIR / "sample_notes.hwp"

    def test_basic_notes_file_exists(self, basic_notes_file):
        assert basic_notes_file.exists()

    def test_extract_footnotes_basic(self, basic_notes_file):
        with HWP5Reader(str(basic_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert isinstance(result, ExtractResult)
            assert len(result.footnotes) == 2

    def test_extract_endnotes_basic(self, basic_notes_file):
        with HWP5Reader(str(basic_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert len(result.endnotes) == 1
            assert result.endnotes[0].text == "sssd"

    def test_footnote_markers_in_text(self, basic_notes_file):
        with HWP5Reader(str(basic_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert "[^1]" in result.text
            assert "[^2]" in result.text

    def test_endnote_markers_in_text(self, basic_notes_file):
        with HWP5Reader(str(basic_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert "[^e1]" in result.text

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwp").exists(),
        reason="Sample notes file not available",
    )
    def test_sample_footnotes_count(self, sample_notes_file):
        with HWP5Reader(str(sample_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert len(result.footnotes) == 2

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwp").exists(),
        reason="Sample notes file not available",
    )
    def test_sample_endnotes_count(self, sample_notes_file):
        with HWP5Reader(str(sample_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert len(result.endnotes) == 3

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwp").exists(),
        reason="Sample notes file not available",
    )
    def test_sample_hyperlinks(self, sample_notes_file):
        with HWP5Reader(str(sample_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert len(result.hyperlinks) == 2

            texts = [h[0] for h in result.hyperlinks]
            urls = [h[1] for h in result.hyperlinks]

            assert "식 현상" in texts
            assert "혼성일식의 원리" in texts
            assert any("britannica.com" in url for url in urls)
            assert any("youtu.be" in url for url in urls)


class TestHWPXNotes:
    """HWPX 각주/미주 추출 테스트"""

    @pytest.fixture
    def sample_notes_file(self):
        return TESTS_DATA_DIR / "sample_notes.hwpx"

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample HWPX notes file not available",
    )
    def test_extract_footnotes(self, sample_notes_file):
        with HWPXReader(str(sample_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert isinstance(result, ExtractResult)
            assert len(result.footnotes) == 2

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample HWPX notes file not available",
    )
    def test_extract_endnotes(self, sample_notes_file):
        with HWPXReader(str(sample_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert len(result.endnotes) == 3

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample HWPX notes file not available",
    )
    def test_extract_hyperlinks(self, sample_notes_file):
        with HWPXReader(str(sample_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert len(result.hyperlinks) == 2

            texts = [h[0] for h in result.hyperlinks]
            urls = [h[1] for h in result.hyperlinks]

            assert "식 현상" in texts
            assert "혼성일식의 원리" in texts
            assert any("britannica.com" in url for url in urls)
            assert any("youtu.be" in url for url in urls)

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample HWPX notes file not available",
    )
    def test_footnote_markers_in_text(self, sample_notes_file):
        with HWPXReader(str(sample_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert "[^1]" in result.text
            assert "[^2]" in result.text

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample HWPX notes file not available",
    )
    def test_endnote_markers_in_text(self, sample_notes_file):
        with HWPXReader(str(sample_notes_file)) as reader:
            result = reader.extract_text_with_notes(ExtractOptions())

            assert "[^e1]" in result.text
            assert "[^e2]" in result.text
            assert "[^e3]" in result.text


class TestHWP5HWPXParity:
    """HWP5와 HWPX 결과 동일성 테스트"""

    @pytest.fixture
    def hwp5_file(self):
        return TESTS_DATA_DIR / "sample_notes.hwp"

    @pytest.fixture
    def hwpx_file(self):
        return TESTS_DATA_DIR / "sample_notes.hwpx"

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwp").exists()
        or not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample files not available",
    )
    def test_footnote_count_parity(self, hwp5_file, hwpx_file):
        with HWP5Reader(str(hwp5_file)) as hwp5_reader:
            hwp5_result = hwp5_reader.extract_text_with_notes(ExtractOptions())

        with HWPXReader(str(hwpx_file)) as hwpx_reader:
            hwpx_result = hwpx_reader.extract_text_with_notes(ExtractOptions())

        assert len(hwp5_result.footnotes) == len(hwpx_result.footnotes)

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwp").exists()
        or not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample files not available",
    )
    def test_endnote_count_parity(self, hwp5_file, hwpx_file):
        with HWP5Reader(str(hwp5_file)) as hwp5_reader:
            hwp5_result = hwp5_reader.extract_text_with_notes(ExtractOptions())

        with HWPXReader(str(hwpx_file)) as hwpx_reader:
            hwpx_result = hwpx_reader.extract_text_with_notes(ExtractOptions())

        assert len(hwp5_result.endnotes) == len(hwpx_result.endnotes)

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwp").exists()
        or not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample files not available",
    )
    def test_hyperlink_count_parity(self, hwp5_file, hwpx_file):
        with HWP5Reader(str(hwp5_file)) as hwp5_reader:
            hwp5_result = hwp5_reader.extract_text_with_notes(ExtractOptions())

        with HWPXReader(str(hwpx_file)) as hwpx_reader:
            hwpx_result = hwpx_reader.extract_text_with_notes(ExtractOptions())

        assert len(hwp5_result.hyperlinks) == len(hwpx_result.hyperlinks)

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwp").exists()
        or not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample files not available",
    )
    def test_hyperlink_text_parity(self, hwp5_file, hwpx_file):
        with HWP5Reader(str(hwp5_file)) as hwp5_reader:
            hwp5_result = hwp5_reader.extract_text_with_notes(ExtractOptions())

        with HWPXReader(str(hwpx_file)) as hwpx_reader:
            hwpx_result = hwpx_reader.extract_text_with_notes(ExtractOptions())

        hwp5_texts = sorted([h[0] for h in hwp5_result.hyperlinks])
        hwpx_texts = sorted([h[0] for h in hwpx_result.hyperlinks])

        assert hwp5_texts == hwpx_texts

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwp").exists()
        or not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample files not available",
    )
    def test_hyperlink_url_parity(self, hwp5_file, hwpx_file):
        with HWP5Reader(str(hwp5_file)) as hwp5_reader:
            hwp5_result = hwp5_reader.extract_text_with_notes(ExtractOptions())

        with HWPXReader(str(hwpx_file)) as hwpx_reader:
            hwpx_result = hwpx_reader.extract_text_with_notes(ExtractOptions())

        hwp5_urls = sorted([h[1] for h in hwp5_result.hyperlinks])
        hwpx_urls = sorted([h[1] for h in hwpx_result.hyperlinks])

        assert hwp5_urls == hwpx_urls


class TestNoteDataStructure:
    """NoteData 구조 테스트"""

    def test_note_data_attributes(self):
        note = NoteData(note_type="footnote", number=1, text="Test note")

        assert note.note_type == "footnote"
        assert note.number == 1
        assert note.text == "Test note"

    def test_extract_result_attributes(self):
        result = ExtractResult(
            text="Sample text",
            footnotes=[NoteData(note_type="footnote", number=1, text="fn1")],
            endnotes=[NoteData(note_type="endnote", number=1, text="en1")],
            hyperlinks=[("link", "http://example.com")],
        )

        assert result.text == "Sample text"
        assert len(result.footnotes) == 1
        assert len(result.endnotes) == 1
        assert len(result.hyperlinks) == 1


class TestHWPXMemos:
    @pytest.fixture
    def sample_hwpx_file(self):
        return TESTS_DATA_DIR / "sample_notes.hwpx"

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample HWPX file not available",
    )
    def test_get_memos_returns_list(self, sample_hwpx_file):
        with HWPXReader(str(sample_hwpx_file)) as reader:
            memos = reader.get_memos()

        assert isinstance(memos, list)

    @pytest.mark.skipif(
        not (TESTS_DATA_DIR / "sample_notes.hwpx").exists(),
        reason="Sample HWPX file not available",
    )
    def test_memos_in_extract_result(self, sample_hwpx_file):
        with HWPXReader(str(sample_hwpx_file)) as reader:
            result = reader.extract_text_with_notes()

        assert isinstance(result.memos, list)
