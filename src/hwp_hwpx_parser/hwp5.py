"""HWP 5.0 Parser (Pure Python, olefile-based)"""

import struct
import zlib
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Union, Dict

try:
    import olefile

    OLEFILE_AVAILABLE = True
except ImportError:
    OLEFILE_AVAILABLE = False
    olefile = None

from .models import (
    ExtractOptions,
    TableData,
    format_image_marker,
    NoteData,
    ExtractResult,
    MemoData,
    ImageData,
    detect_image_format,
)

logger = logging.getLogger(__name__)

FILE_HEADER_STREAM = "FileHeader"
BODY_TEXT_STREAM = "BodyText/Section{}"

HWPTAG_BEGIN = 0x10
HWPTAG_BIN_DATA = HWPTAG_BEGIN + 2
HWPTAG_PARA_TEXT = HWPTAG_BEGIN + 51
HWPTAG_CTRL_HEADER = HWPTAG_BEGIN + 55
HWPTAG_LIST_HEADER = HWPTAG_BEGIN + 56
HWPTAG_TABLE = HWPTAG_BEGIN + 61
HWPTAG_SHAPE_COMPONENT_PICTURE = HWPTAG_BEGIN + 69
HWPTAG_MEMO_LIST = HWPTAG_BEGIN + 77

CTRL_CHAR_FIELD = 17
INLINE_CTRL_EXT_SIZE = 8
EXTENDED_CTRL_EXT_SIZE = 12


def _make_ctrl_id(c1: str, c2: str, c3: str, c4: str) -> int:
    return ord(c1) | (ord(c2) << 8) | (ord(c3) << 16) | (ord(c4) << 24)


CTRL_ID_FOOTNOTE = _make_ctrl_id(" ", " ", "n", "f")
CTRL_ID_ENDNOTE = _make_ctrl_id(" ", " ", "n", "e")
CTRL_ID_HYPERLINK = _make_ctrl_id("k", "l", "h", "%")
CTRL_ID_MEMO = _make_ctrl_id("e", "m", "%", "%")
CTRL_ID_GSO = _make_ctrl_id(" ", "o", "s", "g")


class HWP5Reader:
    """HWP 5.0 file reader (pure Python)."""

    def __init__(self, filepath: Union[str, Path]):
        if not OLEFILE_AVAILABLE:
            raise ImportError("olefile package required: pip install olefile")

        self.filepath = Path(filepath)
        self._ole = None
        self._bin_data_names: List[str] = []
        self._bindata_id_map: Dict[int, str] = {}
        self._image_bindata_queue: List[int] = []
        self._image_index = 0
        self._footnotes: List[NoteData] = []
        self._endnotes: List[NoteData] = []
        self._hyperlinks: List[tuple] = []
        self._memos: List[MemoData] = []
        self._footnote_counter = 0
        self._endnote_counter = 0
        self._processed_hyperlinks = set()
        self._hyperlink_texts = []

    def _open(self):
        if self._ole is None:
            if not olefile.isOleFile(str(self.filepath)):
                raise ValueError(f"Invalid HWP file: {self.filepath}")
            self._ole = olefile.OleFileIO(str(self.filepath))
        return self._ole

    def _close(self):
        if self._ole is not None:
            self._ole.close()
            self._ole = None

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()

    def is_valid(self) -> bool:
        try:
            ole = self._open()
            return ole.exists(FILE_HEADER_STREAM)
        except Exception:
            return False

    def is_encrypted(self) -> bool:
        try:
            ole = self._open()
            if not ole.exists(FILE_HEADER_STREAM):
                return False
            header = ole.openstream(FILE_HEADER_STREAM).read(40)
            if len(header) < 40:
                return False
            properties = struct.unpack_from("<I", header, 36)[0]
            return (properties & 0x02) != 0
        except Exception:
            return False

    def is_compressed(self) -> bool:
        try:
            ole = self._open()
            if not ole.exists(FILE_HEADER_STREAM):
                return True
            header = ole.openstream(FILE_HEADER_STREAM).read(40)
            if len(header) < 40:
                return True
            properties = struct.unpack_from("<I", header, 36)[0]
            return (properties & 0x01) != 0
        except Exception:
            return True

    def _load_bin_data_names(self):
        if self._bin_data_names:
            return
        try:
            ole = self._open()
            for stream_path in ole.listdir():
                if len(stream_path) >= 2 and stream_path[0] == "BinData":
                    self._bin_data_names.append(stream_path[1])
        except Exception:
            pass

    def _load_bindata_id_map(self):
        if self._bindata_id_map:
            return
        try:
            ole = self._open()
            if not ole.exists("DocInfo"):
                return
            docinfo_data = ole.openstream("DocInfo").read()
            try:
                docinfo_data = zlib.decompress(docinfo_data, -15)
            except zlib.error:
                pass

            offset = 0
            while offset < len(docinfo_data) - 4:
                header = struct.unpack_from("<I", docinfo_data, offset)[0]
                tag_id = header & 0x3FF
                size = (header >> 20) & 0xFFF
                offset += 4
                if size == 0xFFF:
                    if offset + 4 > len(docinfo_data):
                        break
                    size = struct.unpack_from("<I", docinfo_data, offset)[0]
                    offset += 4
                if offset + size > len(docinfo_data):
                    break

                if tag_id == HWPTAG_BIN_DATA and size >= 6:
                    record_data = docinfo_data[offset : offset + size]
                    storage_id = struct.unpack_from("<H", record_data, 2)[0]
                    ext_len = struct.unpack_from("<H", record_data, 4)[0]
                    if 6 + ext_len * 2 <= len(record_data):
                        ext = record_data[6 : 6 + ext_len * 2].decode(
                            "utf-16-le", errors="ignore"
                        )
                        filename = f"BIN{storage_id:04X}.{ext}"
                        self._bindata_id_map[storage_id] = filename

                offset += size
        except Exception:
            pass

    def _get_image_name_by_bindata_id(self, bindata_id: int) -> Optional[str]:
        self._load_bindata_id_map()
        return self._bindata_id_map.get(bindata_id)

    def _extract_image_bindata_ids(
        self, records: List[Tuple[int, int, bytes]]
    ) -> List[int]:
        bindata_ids = []
        for tag_id, level, data in records:
            if tag_id == HWPTAG_SHAPE_COMPONENT_PICTURE and len(data) >= 73:
                bindata_id = struct.unpack_from("<H", data, 71)[0]
                if bindata_id > 0:
                    bindata_ids.append(bindata_id)
        return bindata_ids

    def _get_image_name(self, index: int) -> Optional[str]:
        self._load_bin_data_names()
        if index < len(self._bin_data_names):
            return self._bin_data_names[index]
        return None

    def _decompress(self, data: bytes) -> bytes:
        if not self.is_compressed():
            return data
        try:
            return zlib.decompress(data, 15)
        except zlib.error:
            try:
                return zlib.decompress(data, -15)
            except zlib.error:
                return data

    def _iter_sections(self):
        ole = self._open()
        section_idx = 0
        while ole.exists(BODY_TEXT_STREAM.format(section_idx)):
            yield section_idx
            section_idx += 1

    def _read_section(self, section_idx: int) -> bytes:
        ole = self._open()
        stream_name = BODY_TEXT_STREAM.format(section_idx)
        compressed = ole.openstream(stream_name).read()
        return self._decompress(compressed)

    def _parse_records(self, data: bytes):
        offset = 0
        while offset < len(data):
            try:
                header_value = struct.unpack_from("<I", data, offset)[0]
            except struct.error:
                break

            tag_id = header_value & 0x3FF
            level = (header_value >> 10) & 0x3FF
            size = (header_value >> 20) & 0xFFF
            offset += 4

            if size == 0xFFF:
                if offset + 4 > len(data):
                    break
                size = struct.unpack_from("<I", data, offset)[0]
                offset += 4

            if size == 0 or offset + size > len(data):
                offset += size if size > 0 else 0
                continue

            record_data = data[offset : offset + size]
            yield tag_id, level, record_data
            offset += size

    def _reset_counters(self):
        self._image_index = 0
        self._footnotes = []
        self._endnotes = []
        self._hyperlinks = []
        self._memos = []
        self._footnote_counter = 0
        self._endnote_counter = 0
        self._memo_counter = 0
        self._processed_hyperlinks = set()
        self._hyperlink_texts = []

    def extract_text(self, options: Optional[ExtractOptions] = None) -> str:
        options = options or ExtractOptions()
        self._reset_counters()

        if self.is_encrypted():
            raise ValueError("Encrypted files are not supported")

        sections_text = []
        section_files = list(self._iter_sections())

        for section_idx in section_files:
            section_data = self._read_section(section_idx)
            section_text = self._extract_section_text(section_data, options)
            if section_text.strip():
                sections_text.append(section_text)

        return options.paragraph_separator.join(sections_text)

    def extract_text_with_notes(
        self, options: Optional[ExtractOptions] = None
    ) -> ExtractResult:
        text = self.extract_text(options)
        return ExtractResult(
            text=text,
            footnotes=self._footnotes.copy(),
            endnotes=self._endnotes.copy(),
            hyperlinks=self._hyperlinks.copy(),
            memos=self._memos.copy(),
        )

    def get_memos(self) -> List[MemoData]:
        if self.is_encrypted():
            raise ValueError("Encrypted files are not supported")

        memos = []
        memo_counter = 0
        section_files = list(self._iter_sections())
        if not section_files:
            return memos

        last_section_idx = section_files[-1]
        section_data = self._read_section(last_section_idx)
        records = list(self._parse_records(section_data))

        for i, (tag_id, level, record_data) in enumerate(records):
            if tag_id == HWPTAG_MEMO_LIST:
                memo_text = self._extract_memo_text(records, i)
                if memo_text.strip():
                    memo_counter += 1
                    memos.append(
                        MemoData(
                            text=memo_text.strip(),
                            number=memo_counter,
                        )
                    )

        return memos

    def get_tables(self, options: Optional[ExtractOptions] = None) -> List[TableData]:
        options = options or ExtractOptions()
        if self.is_encrypted():
            raise ValueError("Encrypted files are not supported")

        all_tables = []
        for section_idx in self._iter_sections():
            section_data = self._read_section(section_idx)
            tables = self._extract_tables_from_section(section_data, options)
            all_tables.extend(tables)

        return all_tables

    def get_images(self) -> List[ImageData]:
        if self.is_encrypted():
            raise ValueError("Encrypted files are not supported")

        images = []
        ole = self._open()
        self._load_bin_data_names()

        for idx, name in enumerate(self._bin_data_names):
            stream_path = ["BinData", name]
            if ole.exists(stream_path):
                data = ole.openstream(stream_path).read()

                # Always try raw deflate decompression (HWP uses raw deflate, not zlib wrapper)
                try:
                    data = zlib.decompress(data, -15)
                except zlib.error:
                    pass  # Keep original data if decompression fails

                fmt = detect_image_format(data)
                if fmt != "unknown":
                    images.append(
                        ImageData(
                            filename=name,
                            data=data,
                            index=idx,
                            format=fmt,
                        )
                    )
        return images

    def close(self):
        self._close()

    def _extract_memos_from_section(self, data: bytes) -> None:
        records = list(self._parse_records(data))
        for i, (tag_id, level, record_data) in enumerate(records):
            if tag_id == HWPTAG_MEMO_LIST:
                memo_text = self._extract_memo_text(records, i)
                if memo_text.strip():
                    self._memo_counter += 1
                    self._memos.append(
                        MemoData(
                            text=memo_text.strip(),
                            number=self._memo_counter,
                        )
                    )

    def _extract_memo_text(
        self, records: List[Tuple[int, int, bytes]], memo_list_idx: int
    ) -> str:
        texts = []
        start_level = records[memo_list_idx][1] if memo_list_idx < len(records) else 0

        for i in range(memo_list_idx + 1, len(records)):
            tag_id, level, record_data = records[i]
            if tag_id == HWPTAG_MEMO_LIST and level <= start_level:
                break
            if level < start_level:
                break
            if tag_id == HWPTAG_PARA_TEXT:
                text = self._decode_paragraph_plain(record_data)
                if text.strip():
                    texts.append(text.strip())

        return " ".join(texts)

    def _extract_section_text(self, data: bytes, options: ExtractOptions) -> str:
        paragraphs = []
        records = list(self._parse_records(data))
        ctrl_queue = []
        i = 0
        memo_section_level = None
        note_section_level = None

        self._image_bindata_queue = self._extract_image_bindata_ids(records)

        table_ranges = self._find_table_ranges(records)

        self._hyperlink_texts = self._collect_hyperlink_texts(records)

        while i < len(records):
            tag_id, level, record_data = records[i]

            if tag_id == HWPTAG_MEMO_LIST:
                memo_section_level = level
                i += 1
                continue

            if memo_section_level is not None:
                if level < memo_section_level:
                    memo_section_level = None
                else:
                    i += 1
                    continue

            # 각주/미주 섹션 내부 스킵 (본문에서 분리)
            if note_section_level is not None:
                if level <= note_section_level:
                    note_section_level = None  # 섹션 종료
                else:
                    i += 1
                    continue  # 각주/미주 내용 스킵

            if i in table_ranges:
                table_start, table_end = table_ranges[i]
                table_data = self._extract_table_at(records, table_start, options)
                if table_data and table_data.rows:
                    table_text = table_data.format(
                        options.table_style, options.table_delimiter
                    )
                    # 테이블 전후에 빈 줄 추가 (HWPX와 동일한 구조)
                    paragraphs.append("")
                    paragraphs.append(table_text)
                    paragraphs.append("")

                # 표 범위 건너뛰기
                i = table_end + 1
                continue

            if tag_id == HWPTAG_CTRL_HEADER:
                ctrl_id = self._read_ctrl_id(record_data)
                # 각주/미주 섹션 시작 감지
                if ctrl_id in (CTRL_ID_FOOTNOTE, CTRL_ID_ENDNOTE):
                    note_section_level = level
                ctrl_queue.append((ctrl_id, i))

            elif tag_id == HWPTAG_PARA_TEXT:
                para_text = self._decode_paragraph_with_notes(
                    record_data, options, records, i, ctrl_queue
                )
                if para_text.strip() or options.include_empty_paragraphs:
                    paragraphs.append(para_text)

            i += 1

        return options.line_separator.join(paragraphs)

    def _read_ctrl_id(self, record_data: bytes) -> int:
        if len(record_data) >= 4:
            return struct.unpack_from("<I", record_data, 0)[0]
        return 0

    def _find_table_ranges(
        self, records: List[Tuple[int, int, bytes]]
    ) -> Dict[int, Tuple[int, int]]:
        """표의 시작과 끝 인덱스를 미리 계산"""
        table_ranges = {}
        i = 0

        while i < len(records):
            tag_id, level, record_data = records[i]

            if tag_id == HWPTAG_TABLE:
                table_start = i
                parsed = self._parse_table_record(record_data)

                if parsed:
                    rows, cols, row_counts = parsed
                    total_cells = sum(row_counts)

                    # 모든 셀(LIST_HEADER)을 찾을 때까지 진행
                    cells_found = 0
                    j = i + 1
                    table_end = i

                    while j < len(records) and cells_found < total_cells:
                        jtag, jlevel, jdata = records[j]
                        if jtag == HWPTAG_LIST_HEADER:
                            cells_found += 1
                            if cells_found == total_cells:
                                # 마지막 셀 - 이 셀의 끝까지 찾기
                                cell_level = jlevel
                                k = j + 1
                                while k < len(records):
                                    ktag, klevel, kdata = records[k]
                                    if (
                                        klevel <= cell_level
                                        and ktag == HWPTAG_LIST_HEADER
                                    ):
                                        break
                                    if klevel < cell_level:
                                        break
                                    k += 1
                                table_end = k - 1
                                break
                        j += 1

                    if table_end <= table_start:
                        table_end = j - 1 if j > i else i

                    table_ranges[table_start] = (table_start, table_end)
                    i = table_end + 1
                    continue

            i += 1

        return table_ranges

    def _extract_table_at(
        self,
        records: List[Tuple[int, int, bytes]],
        table_record_idx: int,
        options: ExtractOptions,
    ) -> Optional[TableData]:
        tag_id, level, record_data = records[table_record_idx]
        if tag_id != HWPTAG_TABLE:
            return None

        table_info = self._parse_table_record(record_data)
        if not table_info:
            return None

        rows, cols, row_counts = table_info
        total_cells = sum(row_counts)

        cells_text = []
        cell_idx = 0
        j = table_record_idx + 1
        note_section_level = None

        while j < len(records) and cell_idx < total_cells:
            cell_tag, cell_level, cell_data = records[j]

            if note_section_level is not None:
                if cell_level <= note_section_level:
                    note_section_level = None
                else:
                    j += 1
                    continue

            if cell_tag == HWPTAG_CTRL_HEADER:
                ctrl_id = self._read_ctrl_id(cell_data)
                if ctrl_id in (CTRL_ID_FOOTNOTE, CTRL_ID_ENDNOTE):
                    note_section_level = cell_level
                    j += 1
                    continue

            if cell_tag == HWPTAG_LIST_HEADER:
                cell_text = self._extract_cell_text(records, j, options)
                cells_text.append(cell_text)
                cell_idx += 1
            j += 1

        if cells_text:
            return self._build_table_data(rows, cols, row_counts, cells_text)
        return None

    def _decode_paragraph_with_notes(
        self,
        record_data: bytes,
        options: ExtractOptions,
        records: List[Tuple[int, int, bytes]],
        para_record_idx: int,
        ctrl_queue: List[Tuple[int, int]],
    ) -> str:
        footnote_positions = self._find_note_markers(record_data, CTRL_ID_FOOTNOTE)
        endnote_positions = self._find_note_markers(record_data, CTRL_ID_ENDNOTE)
        memo_markers = self._find_memo_markers(record_data)

        for pos in footnote_positions:
            self._footnote_counter += 1
            fn_text = self._find_note_text(
                records, CTRL_ID_FOOTNOTE, self._footnote_counter
            )
            self._footnotes.append(
                NoteData(
                    note_type="footnote", number=self._footnote_counter, text=fn_text
                )
            )

        for pos in endnote_positions:
            self._endnote_counter += 1
            en_text = self._find_note_text(
                records, CTRL_ID_ENDNOTE, self._endnote_counter
            )
            self._endnotes.append(
                NoteData(
                    note_type="endnote", number=self._endnote_counter, text=en_text
                )
            )

        for pos, ref_text in memo_markers:
            self._memo_counter += 1
            memo_text = self._find_memo_content(records, self._memo_counter)
            self._memos.append(
                MemoData(
                    text=memo_text,
                    number=self._memo_counter,
                    referenced_text=ref_text if ref_text else None,
                )
            )

        self._extract_hyperlinks_from_queue(ctrl_queue, records)
        is_image_gso = self._has_image_gso(record_data, records, para_record_idx)
        return self._decode_paragraph_text_with_markers(
            record_data,
            options,
            footnote_positions,
            endnote_positions,
            memo_markers,
            is_image_gso,
        )

    def _find_note_markers(self, data: bytes, target_ctrl_id: int) -> List[int]:
        positions = []
        i = 0
        while i < len(data) - 5:
            code = struct.unpack_from("<H", data, i)[0]
            if code == CTRL_CHAR_FIELD:
                ctrl_id = struct.unpack_from("<I", data, i + 2)[0]
                if ctrl_id == target_ctrl_id:
                    positions.append(i)
            i += 2
        return positions

    def _find_memo_markers(self, data: bytes) -> List[Tuple[int, str]]:
        markers = []
        i = 0
        while i < len(data) - 5:
            code = struct.unpack_from("<H", data, i)[0]
            if code == 3:
                ctrl_id = struct.unpack_from("<I", data, i + 2)[0]
                if ctrl_id == CTRL_ID_MEMO:
                    ref_text = self._extract_memo_ref_text(data, i + 14)
                    markers.append((i, ref_text))
            i += 2
        return markers

    def _extract_memo_ref_text(self, data: bytes, start: int) -> str:
        chars = []
        i = start
        if i < len(data) - 1:
            code = struct.unpack_from("<H", data, i)[0]
            if code == 3:
                i += 2
        while i < len(data) - 1:
            code = struct.unpack_from("<H", data, i)[0]
            if code == 4:
                break
            elif code >= 32:
                chars.append(chr(code))
            i += 2
        return "".join(chars)

    def _skip_memo_field(self, data: bytes, start: int) -> int:
        i = start + 14
        if i < len(data) - 1:
            code = struct.unpack_from("<H", data, i)[0]
            if code == 3:
                i += 2
        while i < len(data) - 1:
            code = struct.unpack_from("<H", data, i)[0]
            if code == 4:
                i += 14
                if i < len(data) - 1:
                    next_code = struct.unpack_from("<H", data, i)[0]
                    if next_code == 4:
                        i += 2
                break
            i += 2
        return i

    def _decode_paragraph_text_with_markers(
        self,
        record_data: bytes,
        options: ExtractOptions,
        footnote_positions: List[int],
        endnote_positions: List[int],
        memo_markers: Optional[List[Tuple[int, str]]] = None,
        is_image_gso: bool = False,
    ) -> str:
        note_positions = set(footnote_positions + endnote_positions)
        memo_positions = {pos: ref_text for pos, ref_text in (memo_markers or [])}
        chars = []
        i = 0
        fn_count = 0
        en_count = 0
        memo_count = 0

        fn_start = self._footnote_counter - len(footnote_positions)
        en_start = self._endnote_counter - len(endnote_positions)
        memo_start = self._memo_counter - len(memo_markers or [])

        while i < len(record_data) - 1:
            code = struct.unpack_from("<H", record_data, i)[0]

            if i in footnote_positions:
                fn_count += 1
                chars.append(f"[^{fn_start + fn_count}]")
                i += 2 + EXTENDED_CTRL_EXT_SIZE
                continue
            elif i in endnote_positions:
                en_count += 1
                chars.append(f"[^e{en_start + en_count}]")
                i += 2 + EXTENDED_CTRL_EXT_SIZE
                continue
            elif i in memo_positions:
                memo_count += 1
                memo_num = memo_start + memo_count
                ref_text = memo_positions[i]
                chars.append(ref_text)
                chars.append(f"[MEMO:{memo_num}]")
                i = self._skip_memo_field(record_data, i)
                continue

            i += 2

            if code < 8:
                if code == 0:
                    pass
                elif code in (2, 3, 4):
                    if i + 2 <= len(record_data) - 1:
                        next_code = struct.unpack_from("<H", record_data, i)[0]
                        if (
                            0x0020 <= next_code <= 0x007E
                            or 0xAC00 <= next_code <= 0xD7AF
                            or 0x3130 <= next_code <= 0x318F
                            or next_code in (3, 4, 11, 12, 13)
                            or 15 <= next_code <= 23
                        ):
                            pass
                        else:
                            i += EXTENDED_CTRL_EXT_SIZE
                    else:
                        i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += INLINE_CTRL_EXT_SIZE
            elif code == 9:
                chars.append("\t")
            elif code == 10 or code == 13:
                pass
            elif 11 <= code <= 12:
                if code == 11:
                    if i + 4 <= len(record_data):
                        ctrl_id = struct.unpack_from("<I", record_data, i)[0]
                        if ctrl_id == CTRL_ID_GSO:
                            marker = self._handle_control_char(code, options)
                            if marker:
                                chars.append(marker)
                            i += EXTENDED_CTRL_EXT_SIZE
                        elif self._is_valid_ctrl_id(ctrl_id):
                            i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += INLINE_CTRL_EXT_SIZE
            elif code == CTRL_CHAR_FIELD:
                if i + 4 <= len(record_data):
                    ctrl_id = struct.unpack_from("<I", record_data, i)[0]
                    if ctrl_id in (
                        CTRL_ID_FOOTNOTE,
                        CTRL_ID_ENDNOTE,
                        CTRL_ID_HYPERLINK,
                    ):
                        i += EXTENDED_CTRL_EXT_SIZE
                    elif self._is_valid_ctrl_id(ctrl_id):
                        i += EXTENDED_CTRL_EXT_SIZE
                    else:
                        pass
                else:
                    i += EXTENDED_CTRL_EXT_SIZE
            elif 15 <= code <= 23:
                if i + 2 <= len(record_data) - 1:
                    next_code = struct.unpack_from("<H", record_data, i)[0]
                    if (
                        0x0020 <= next_code <= 0x007E
                        or 0xAC00 <= next_code <= 0xD7AF
                        or 0x3130 <= next_code <= 0x318F
                        or next_code in (3, 4, 11, 12, 13)
                        or 15 <= next_code <= 23
                    ):
                        pass
                    else:
                        i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += EXTENDED_CTRL_EXT_SIZE
            elif code < 32:
                pass
            else:
                if self._is_valid_char(code):
                    chars.append(chr(code))

        return "".join(chars)

    def _find_note_text(
        self,
        records: List[Tuple[int, int, bytes]],
        target_ctrl_id: int,
        occurrence: int,
    ) -> str:
        count = 0
        for i, (tag_id, level, record_data) in enumerate(records):
            if tag_id == HWPTAG_CTRL_HEADER:
                ctrl_id = self._read_ctrl_id(record_data)
                if ctrl_id == target_ctrl_id:
                    count += 1
                    if count == occurrence:
                        return self._extract_note_text(records, i)
        return ""

    def _find_memo_content(
        self,
        records: List[Tuple[int, int, bytes]],
        occurrence: int,
    ) -> str:
        count = 0
        for i, (tag_id, level, record_data) in enumerate(records):
            if tag_id == HWPTAG_MEMO_LIST:
                count += 1
                if count == occurrence:
                    return self._extract_memo_text(records, i)
        return ""

    def _extract_note_text(
        self, records: List[Tuple[int, int, bytes]], ctrl_record_idx: int
    ) -> str:
        texts = []
        start_level = (
            records[ctrl_record_idx][1] if ctrl_record_idx < len(records) else 0
        )

        for i in range(ctrl_record_idx + 1, min(ctrl_record_idx + 50, len(records))):
            tag_id, level, record_data = records[i]
            if level <= start_level:
                break
            if tag_id == HWPTAG_PARA_TEXT and level > start_level:
                text = self._decode_paragraph_plain(record_data)
                if text.strip():
                    texts.append(text.strip())

        return " ".join(texts)

    def _extract_hyperlinks_from_queue(
        self, ctrl_queue: List[Tuple[int, int]], records: List[Tuple[int, int, bytes]]
    ) -> None:
        for ctrl_id, ctrl_record_idx in ctrl_queue:
            if ctrl_id == CTRL_ID_HYPERLINK:
                if ctrl_record_idx in self._processed_hyperlinks:
                    continue
                self._processed_hyperlinks.add(ctrl_record_idx)
                hyperlink_data = self._extract_hyperlink_data(records, ctrl_record_idx)
                if hyperlink_data:
                    self._hyperlinks.append(hyperlink_data)

    def _collect_hyperlink_texts(
        self, records: List[Tuple[int, int, bytes]]
    ) -> List[str]:
        texts = []
        for tag_id, _, record_data in records:
            if tag_id == HWPTAG_PARA_TEXT:
                texts.extend(self._extract_hyperlink_texts_from_para(record_data))
        return texts

    def _extract_hyperlink_texts_from_para(self, para_data: bytes) -> List[str]:
        hyperlink_texts = []
        i = 0

        while i < len(para_data) - 1:
            code = struct.unpack_from("<H", para_data, i)[0]

            if code == 0x03:
                if i + 6 <= len(para_data):
                    ctrl_id = struct.unpack_from("<I", para_data, i + 2)[0]

                    if ctrl_id == CTRL_ID_HYPERLINK:
                        text_start = i + 14
                        text_chars = []
                        j = text_start

                        while j < len(para_data) - 1:
                            c = struct.unpack_from("<H", para_data, j)[0]
                            if c == 0x04:
                                break
                            elif c == 0x03:
                                j += 2
                            elif 0x20 <= c < 0x10000:
                                text_chars.append(chr(c))
                                j += 2
                            else:
                                j += 2

                        if text_chars:
                            hyperlink_texts.append("".join(text_chars))
                        i = j
                        continue
                    else:
                        i += 14
                        continue
            elif code == 0x04:
                i += 10
            elif code < 32:
                if code in (11, 12):
                    i += 10
                elif 15 <= code <= 23:
                    i += 14
                else:
                    i += 2
            else:
                i += 2

        return hyperlink_texts

    def _extract_hyperlink_data(
        self, records: List[Tuple[int, int, bytes]], ctrl_record_idx: int
    ) -> Optional[Tuple[str, str]]:
        if ctrl_record_idx >= len(records):
            return None

        _, _, ctrl_data = records[ctrl_record_idx]
        if len(ctrl_data) < 11:
            return None

        url = self._try_extract_url_from_ctrl(ctrl_data)
        if not url:
            return None

        link_text = self._hyperlink_texts.pop(0) if self._hyperlink_texts else ""
        return (link_text, url) if link_text else None

    def _try_extract_url_from_ctrl(self, ctrl_data: bytes) -> Optional[str]:
        if len(ctrl_data) < 11:
            return None
        try:
            str_len = struct.unpack_from("<H", ctrl_data, 9)[0]
            if str_len <= 0 or 11 + str_len * 2 > len(ctrl_data):
                return None

            command = ctrl_data[11 : 11 + str_len * 2].decode(
                "utf-16-le", errors="ignore"
            )
            url = command.replace("\\:", ":").replace("\\?", "?").replace("\\;", ";")
            if ";" in url:
                url = url.split(";")[0]

            if url.startswith(("http://", "https://", "www.", "mailto:")):
                return url
        except Exception:
            pass
        return None

    def _handle_control_char(self, code: int, options: ExtractOptions) -> Optional[str]:
        if code == 11:
            if self._image_index < len(self._image_bindata_queue):
                bindata_id = self._image_bindata_queue[self._image_index]
                image_name = self._get_image_name_by_bindata_id(bindata_id)
                if not image_name:
                    image_name = self._get_image_name(self._image_index)
            else:
                image_name = self._get_image_name(self._image_index)
            if image_name:
                self._image_index += 1
                return format_image_marker(
                    options.image_marker, image_name, self._image_index
                )
        return None

    def _has_image_gso(
        self,
        record_data: bytes,
        records: List[Tuple[int, int, bytes]],
        para_record_idx: int,
    ) -> bool:
        has_code_11 = False
        i = 0
        while i < len(record_data) - 1:
            code = struct.unpack_from("<H", record_data, i)[0]
            if code == 11:
                has_code_11 = True
                break
            i += 2

        if not has_code_11:
            return False

        for j in range(para_record_idx + 1, min(para_record_idx + 20, len(records))):
            tag_id, level, data = records[j]
            if tag_id == HWPTAG_CTRL_HEADER and len(data) >= 4:
                ctrl_id = struct.unpack_from("<I", data, 0)[0]
                return ctrl_id == CTRL_ID_GSO
        return False

    def _is_valid_ctrl_id(self, ctrl_id: int) -> bool:
        for j in range(4):
            byte = (ctrl_id >> (8 * j)) & 0xFF
            if not (0x20 <= byte <= 0x7E):
                return False
        return True

    def _is_valid_char(self, code: int) -> bool:
        return (
            0x0020 <= code <= 0x007E  # Basic Latin
            or 0x00A0 <= code <= 0x00FF  # Latin-1 Supplement
            or 0x1100 <= code <= 0x11FF  # Hangul Jamo
            or 0x2000 <= code <= 0x206F  # General Punctuation
            or 0x2190 <= code <= 0x21FF  # Arrows (→, ⇨, ←, ↑, ↓)
            or 0x2200 <= code <= 0x22FF  # Mathematical Operators (⋅, ×, ÷, ±)
            or 0x2300 <= code <= 0x23FF  # Miscellaneous Technical
            or 0x2460 <= code <= 0x24FF  # Enclosed Alphanumerics (①, ②, ③)
            or 0x2500 <= code <= 0x257F  # Box Drawing
            or 0x25A0 <= code <= 0x25FF  # Geometric Shapes (■, □, ●, ○)
            or 0x2600 <= code <= 0x26FF  # Miscellaneous Symbols
            or 0x3000 <= code <= 0x303F  # CJK Symbols and Punctuation
            or 0x3130 <= code <= 0x318F  # Hangul Compatibility Jamo
            or 0x3200 <= code <= 0x32FF  # Enclosed CJK Letters (㉠, ㉡, ㉢, ㈀)
            or 0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs (한자)
            or 0xAC00 <= code <= 0xD7AF  # Hangul Syllables
            or 0xFF00 <= code <= 0xFFEF  # Halfwidth and Fullwidth Forms
        )

    def _is_valid_char_strict(self, code: int) -> bool:
        return (
            0x0020 <= code <= 0x007E  # Basic Latin
            or 0x00A0 <= code <= 0x00FF  # Latin-1 Supplement
            or 0x1100 <= code <= 0x11FF  # Hangul Jamo
            or 0x2000 <= code <= 0x206F  # General Punctuation
            or 0x2190 <= code <= 0x21FF  # Arrows (→, ⇨, ←, ↑, ↓)
            or 0x2200 <= code <= 0x22FF  # Mathematical Operators (⋅, ×, ÷, ±)
            or 0x2300 <= code <= 0x23FF  # Miscellaneous Technical
            or 0x2460 <= code <= 0x24FF  # Enclosed Alphanumerics (①, ②, ③)
            or 0x2500 <= code <= 0x257F  # Box Drawing
            or 0x25A0 <= code <= 0x25FF  # Geometric Shapes (■, □, ●, ○)
            or 0x2600 <= code <= 0x26FF  # Miscellaneous Symbols
            or 0x3000 <= code <= 0x303F  # CJK Symbols and Punctuation
            or 0x3130 <= code <= 0x318F  # Hangul Compatibility Jamo
            or 0x3200 <= code <= 0x32FF  # Enclosed CJK Letters (㉠, ㉡, ㉢, ㈀)
            or 0xAC00 <= code <= 0xD7AF  # Hangul Syllables
            or 0xFF00 <= code <= 0xFFEF  # Halfwidth and Fullwidth Forms
        )

    def _decode_paragraph_plain(self, record_data: bytes) -> str:
        chars = []
        i = 0
        while i < len(record_data) - 1:
            code = struct.unpack_from("<H", record_data, i)[0]
            i += 2
            if code < 8:
                if code == 0:
                    pass
                elif code in (2, 3, 4):
                    if i + 2 <= len(record_data) - 1:
                        next_code = struct.unpack_from("<H", record_data, i)[0]
                        if (
                            0x0020 <= next_code <= 0x007E
                            or 0xAC00 <= next_code <= 0xD7AF
                            or 0x3130 <= next_code <= 0x318F
                            or next_code in (3, 4, 11, 12, 13)
                            or 15 <= next_code <= 23
                        ):
                            pass
                        else:
                            i += EXTENDED_CTRL_EXT_SIZE
                    else:
                        i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += INLINE_CTRL_EXT_SIZE
            elif code == 9:
                chars.append(" ")
            elif 15 <= code <= 23:
                if i + 2 <= len(record_data) - 1:
                    next_code = struct.unpack_from("<H", record_data, i)[0]
                    if (
                        0x0020 <= next_code <= 0x007E
                        or 0xAC00 <= next_code <= 0xD7AF
                        or 0x3130 <= next_code <= 0x318F
                        or next_code in (3, 4, 11, 12, 13)
                        or 15 <= next_code <= 23
                    ):
                        pass
                    else:
                        i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += EXTENDED_CTRL_EXT_SIZE
            elif code >= 32 and self._is_valid_char(code):
                chars.append(chr(code))
        return "".join(chars)

    def _decode_paragraph_plain_for_table(self, record_data: bytes) -> str:
        chars = []
        i = 0
        while i < len(record_data) - 1:
            code = struct.unpack_from("<H", record_data, i)[0]
            i += 2
            if code < 8:
                if code == 0:
                    pass
                elif code in (2, 3, 4):
                    if i + 2 <= len(record_data) - 1:
                        next_code = struct.unpack_from("<H", record_data, i)[0]
                        if (
                            0x0020 <= next_code <= 0x007E
                            or 0xAC00 <= next_code <= 0xD7AF
                            or 0x3130 <= next_code <= 0x318F
                            or next_code in (3, 4, 11, 12, 13)
                            or 15 <= next_code <= 23
                        ):
                            pass
                        else:
                            i += EXTENDED_CTRL_EXT_SIZE
                    else:
                        i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += INLINE_CTRL_EXT_SIZE
            elif code == 9:
                chars.append(" ")
            elif 15 <= code <= 23:
                if i + 2 <= len(record_data) - 1:
                    next_code = struct.unpack_from("<H", record_data, i)[0]
                    if (
                        0x0020 <= next_code <= 0x007E
                        or 0xAC00 <= next_code <= 0xD7AF
                        or 0x3130 <= next_code <= 0x318F
                        or next_code in (3, 4, 11, 12, 13)
                        or 15 <= next_code <= 23
                    ):
                        pass
                    else:
                        i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += EXTENDED_CTRL_EXT_SIZE
            elif code >= 32 and self._is_valid_char_strict(code):
                chars.append(chr(code))
        return "".join(chars)

    def _decode_cell_paragraph_with_markers(
        self,
        record_data: bytes,
        records: List[Tuple[int, int, bytes]],
        options: ExtractOptions,
    ) -> str:
        footnote_positions = self._find_note_markers(record_data, CTRL_ID_FOOTNOTE)
        endnote_positions = self._find_note_markers(record_data, CTRL_ID_ENDNOTE)

        for pos in footnote_positions:
            self._footnote_counter += 1
            fn_text = self._find_note_text(
                records, CTRL_ID_FOOTNOTE, self._footnote_counter
            )
            self._footnotes.append(
                NoteData(
                    note_type="footnote", number=self._footnote_counter, text=fn_text
                )
            )

        for pos in endnote_positions:
            self._endnote_counter += 1
            en_text = self._find_note_text(
                records, CTRL_ID_ENDNOTE, self._endnote_counter
            )
            self._endnotes.append(
                NoteData(
                    note_type="endnote", number=self._endnote_counter, text=en_text
                )
            )

        note_positions = set(footnote_positions + endnote_positions)
        chars = []
        i = 0
        fn_count = 0
        en_count = 0
        fn_start = self._footnote_counter - len(footnote_positions)
        en_start = self._endnote_counter - len(endnote_positions)

        while i < len(record_data) - 1:
            code = struct.unpack_from("<H", record_data, i)[0]

            if i in footnote_positions:
                fn_count += 1
                chars.append(f"[^{fn_start + fn_count}]")
                i += 2 + EXTENDED_CTRL_EXT_SIZE
                continue
            elif i in endnote_positions:
                en_count += 1
                chars.append(f"[^e{en_start + en_count}]")
                i += 2 + EXTENDED_CTRL_EXT_SIZE
                continue

            i += 2
            if code < 8:
                if code == 0:
                    pass
                elif code in (2, 3, 4):
                    if i + 2 <= len(record_data) - 1:
                        next_code = struct.unpack_from("<H", record_data, i)[0]
                        if (
                            0x0020 <= next_code <= 0x007E
                            or 0xAC00 <= next_code <= 0xD7AF
                            or 0x3130 <= next_code <= 0x318F
                            or next_code in (3, 4, 11, 12, 13)
                            or 15 <= next_code <= 23
                        ):
                            pass
                        else:
                            i += EXTENDED_CTRL_EXT_SIZE
                    else:
                        i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += INLINE_CTRL_EXT_SIZE
            elif code == 9:
                chars.append(" ")
            elif code == 10 or code == 13:
                pass
            elif 11 <= code <= 12:
                if code == 11:
                    if i + 4 <= len(record_data):
                        ctrl_id = struct.unpack_from("<I", record_data, i)[0]
                        if ctrl_id == CTRL_ID_GSO:
                            marker = self._handle_control_char(code, options)
                            if marker:
                                chars.append(marker)
                            i += EXTENDED_CTRL_EXT_SIZE
                        elif self._is_valid_ctrl_id(ctrl_id):
                            i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += INLINE_CTRL_EXT_SIZE
            elif 15 <= code <= 23:
                if i + 2 <= len(record_data) - 1:
                    next_code = struct.unpack_from("<H", record_data, i)[0]
                    if (
                        0x0020 <= next_code <= 0x007E
                        or 0xAC00 <= next_code <= 0xD7AF
                        or 0x3130 <= next_code <= 0x318F
                        or next_code in (3, 4, 11, 12, 13)
                        or 15 <= next_code <= 23
                    ):
                        pass
                    else:
                        i += EXTENDED_CTRL_EXT_SIZE
                else:
                    i += EXTENDED_CTRL_EXT_SIZE
            elif code >= 32 and self._is_valid_char_strict(code):
                chars.append(chr(code))
        return "".join(chars)

    def _extract_tables_from_section(
        self, data: bytes, options: ExtractOptions
    ) -> List[TableData]:
        tables = []
        records = list(self._parse_records(data))

        i = 0
        while i < len(records):
            tag_id, level, record_data = records[i]

            if tag_id == HWPTAG_TABLE:
                table_info = self._parse_table_record(record_data)
                if table_info:
                    rows, cols, row_counts = table_info
                    total_cells = sum(row_counts)

                    cells_text = []
                    cell_idx = 0
                    j = i + 1

                    while j < len(records) and cell_idx < total_cells:
                        cell_tag, cell_level, cell_data = records[j]
                        if cell_tag == HWPTAG_LIST_HEADER:
                            cell_text = self._extract_cell_text(records, j, options)
                            cells_text.append(cell_text)
                            cell_idx += 1
                        j += 1

                    if cells_text:
                        table_data = self._build_table_data(
                            rows, cols, row_counts, cells_text
                        )
                        if table_data.rows:
                            tables.append(table_data)

            i += 1

        return tables

    def _parse_table_record(self, data: bytes) -> Optional[Tuple[int, int, List[int]]]:
        if len(data) < 14:
            return None

        try:
            rows = struct.unpack_from("<H", data, 4)[0]
            cols = struct.unpack_from("<H", data, 6)[0]

            offset = 18
            row_counts = []

            for _ in range(rows):
                if offset + 2 > len(data):
                    break
                count = struct.unpack_from("<H", data, offset)[0]
                row_counts.append(count)
                offset += 2

            if len(row_counts) != rows:
                row_counts = [cols] * rows

            return rows, cols, row_counts
        except struct.error:
            return None

    def _extract_cell_text(
        self,
        records: List[Tuple[int, int, bytes]],
        start_idx: int,
        options: ExtractOptions,
    ) -> str:
        texts = []
        cell_level = records[start_idx][1]
        nested_table_start = None
        nested_table_level = None
        note_section_level = None

        i = start_idx + 1
        while i < len(records):
            tag_id, level, record_data = records[i]
            if level < cell_level:
                if nested_table_level is not None and nested_table_start is not None:
                    nested_table = self._extract_table_at(
                        records, nested_table_start, options
                    )
                    if nested_table and nested_table.rows:
                        texts.append(nested_table.to_inline())
                    nested_table_level = None
                    nested_table_start = None
                break
            if tag_id == HWPTAG_LIST_HEADER and level <= cell_level:
                break
            if tag_id == HWPTAG_TABLE and level <= cell_level:
                break

            if note_section_level is not None:
                if level <= note_section_level:
                    note_section_level = None
                else:
                    i += 1
                    continue

            if tag_id == HWPTAG_CTRL_HEADER and level > cell_level:
                ctrl_id = self._read_ctrl_id(record_data)
                if ctrl_id in (CTRL_ID_FOOTNOTE, CTRL_ID_ENDNOTE):
                    note_section_level = level
                    i += 1
                    continue

            if tag_id == HWPTAG_TABLE and level > cell_level:
                nested_table = self._extract_table_at(records, i, options)
                if nested_table and nested_table.rows:
                    texts.append(nested_table.to_inline())
                nested_table_level = level
                i += 1
                while i < len(records) and records[i][1] >= nested_table_level:
                    i += 1
                nested_table_level = None
                continue

            if tag_id == HWPTAG_PARA_TEXT and level > cell_level:
                text = self._decode_cell_paragraph_with_markers(
                    record_data, records, options
                )
                if text.strip():
                    texts.append(text.strip())

            i += 1

        if nested_table_level is not None and nested_table_start is not None:
            nested_table = self._extract_table_at(records, nested_table_start, options)
            if nested_table and nested_table.rows:
                texts.append(nested_table.to_inline())

        return " ".join(texts)

    def _build_table_data(
        self, rows: int, cols: int, row_counts: List[int], cells_text: List[str]
    ) -> TableData:
        table_rows = []
        cell_idx = 0

        for row_idx in range(rows):
            num_cols = row_counts[row_idx] if row_idx < len(row_counts) else cols
            row_cells = []

            for col_idx in range(num_cols):
                if cell_idx < len(cells_text):
                    row_cells.append(cells_text[cell_idx])
                    cell_idx += 1
                else:
                    row_cells.append("")

            if row_cells:
                table_rows.append(row_cells)

        return TableData(rows=table_rows)


def extract_hwp5(
    filepath: Union[str, Path], options: Optional[ExtractOptions] = None
) -> Tuple[str, Optional[str]]:
    """
    Extract text from HWP 5.0 file.

    Returns:
        tuple: (text, error_message) - error is None on success
    """
    try:
        with HWP5Reader(str(filepath)) as reader:
            if reader.is_encrypted():
                return "", "Password protected file"
            text = reader.extract_text(options)
            return text, None
    except ImportError as e:
        return "", f"Missing package: {e}"
    except Exception as e:
        return "", f"Extraction failed: {e}"
