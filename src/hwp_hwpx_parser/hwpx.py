"""HWPX Parser (Pure Python, ZIP/XML-based)"""

import zipfile
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union

from .models import (
    ExtractOptions,
    TableData,
    format_image_marker,
    NoteData,
    ExtractResult,
    MemoData,
)

logger = logging.getLogger(__name__)

MANIFEST_PATH = "META-INF/manifest.xml"
CONTENT_SECTION_PREFIX = "Contents/section"


class HWPXReader:
    """HWPX file reader (pure Python)."""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)
        self._zipfile = None
        self._image_index = 0
        self._bin_item_map: Dict[str, str] = {}
        self._footnotes: List[NoteData] = []
        self._endnotes: List[NoteData] = []
        self._hyperlinks: List[tuple] = []
        self._memos: List[MemoData] = []
        self._footnote_counter = 0
        self._endnote_counter = 0
        self._memo_properties: Dict[str, Dict[str, Any]] = {}

    def _open(self):
        if self._zipfile is None:
            if not zipfile.is_zipfile(str(self.filepath)):
                raise ValueError(f"Invalid HWPX file: {self.filepath}")
            self._zipfile = zipfile.ZipFile(str(self.filepath), "r")
        return self._zipfile

    def _close(self):
        if self._zipfile is not None:
            self._zipfile.close()
            self._zipfile = None

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()

    def is_valid(self) -> bool:
        try:
            zf = self._open()
            return any(
                name.startswith(CONTENT_SECTION_PREFIX) for name in zf.namelist()
            )
        except Exception:
            return False

    def is_encrypted(self) -> bool:
        try:
            zf = self._open()
            if MANIFEST_PATH not in zf.namelist():
                return False
            manifest = zf.read(MANIFEST_PATH)
            return b"encryption-data" in manifest.lower()
        except Exception:
            return False

    def _get_section_files(self) -> List[str]:
        zf = self._open()
        section_files = [
            name
            for name in zf.namelist()
            if name.startswith(CONTENT_SECTION_PREFIX) and name.endswith(".xml")
        ]
        return sorted(section_files)

    def _load_bin_item_map(self):
        if self._bin_item_map:
            return

        try:
            zf = self._open()
            header_path = "Contents/header.xml"
            if header_path not in zf.namelist():
                return

            header_xml = zf.read(header_path)
            root = ET.fromstring(header_xml)

            for elem in root.iter():
                tag = self._local_name(elem.tag)
                if tag == "binItem":
                    item_id = elem.get("id", "")
                    src = elem.get("src", "")
                    if item_id and src:
                        filename = src.split("/")[-1] if "/" in src else src
                        self._bin_item_map[item_id] = filename
        except Exception:
            pass

    def _get_image_filename(self, ref_id: str) -> Optional[str]:
        self._load_bin_item_map()
        return self._bin_item_map.get(ref_id)

    def _local_name(self, tag: str) -> str:
        if "}" in tag:
            return tag.split("}")[1]
        return tag

    def _reset_counters(self):
        self._image_index = 0
        self._footnotes = []
        self._endnotes = []
        self._hyperlinks = []
        self._memos = []
        self._footnote_counter = 0
        self._endnote_counter = 0
        self._memo_properties = {}

    def extract_text(self, options: Optional[ExtractOptions] = None) -> str:
        options = options or ExtractOptions()
        self._reset_counters()
        self._load_memo_properties()

        if self.is_encrypted():
            raise ValueError("Encrypted files are not supported")

        sections_text = []

        for section_file in self._get_section_files():
            section_text = self._extract_section(section_file, options)
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

        self._load_memo_properties()
        memos = []

        for section_file in self._get_section_files():
            zf = self._open()
            xml_content = zf.read(section_file)
            root = ET.fromstring(xml_content)
            section_memos = self._extract_memos_from_element(root)
            memos.extend(section_memos)

        return memos

    def get_tables(self, options: Optional[ExtractOptions] = None) -> List[TableData]:
        options = options or ExtractOptions()
        tables = []

        for section_file in self._get_section_files():
            zf = self._open()
            xml_content = zf.read(section_file)
            root = ET.fromstring(xml_content)

            for elem in root.iter():
                tag = self._local_name(elem.tag)
                if tag == "tbl":
                    table_data = self._extract_table(elem)
                    if table_data.rows:
                        tables.append(table_data)

        return tables

    def close(self):
        self._close()

    def _load_memo_properties(self):
        if self._memo_properties:
            return

        try:
            zf = self._open()
            header_path = "Contents/header.xml"
            if header_path not in zf.namelist():
                return

            header_xml = zf.read(header_path)
            root = ET.fromstring(header_xml)

            for elem in root.iter():
                tag = self._local_name(elem.tag)
                if tag == "memoPr":
                    memo_id = elem.get("id", "")
                    if memo_id:
                        self._memo_properties[memo_id] = {
                            "width": elem.get("width"),
                            "fillColor": elem.get("fillColor"),
                            "lineColor": elem.get("lineColor"),
                        }
        except Exception:
            pass

    def _extract_memos_from_element(self, root: ET.Element) -> List[MemoData]:
        memos = []
        current_memo_id = None
        memo_text_parts = []

        for elem in root.iter():
            tag = self._local_name(elem.tag)

            if tag == "fieldBegin":
                field_type = elem.get("type", "")
                if field_type == "MEMO":
                    current_memo_id = elem.get("id") or elem.get("name")
                    memo_text_parts = []

            elif tag == "t" and elem.text and current_memo_id:
                memo_text_parts.append(elem.text)

            elif tag == "fieldEnd" and current_memo_id:
                memo_text = "".join(memo_text_parts).strip()
                if memo_text:
                    props = self._memo_properties.get(current_memo_id, {})
                    memos.append(
                        MemoData(
                            text=memo_text,
                            memo_id=current_memo_id,
                            width=int(props.get("width"))
                            if props.get("width")
                            else None,
                            fill_color=props.get("fillColor"),
                        )
                    )
                current_memo_id = None
                memo_text_parts = []

        return memos

    def _extract_section(self, section_file: str, options: ExtractOptions) -> str:
        zf = self._open()
        xml_content = zf.read(section_file)
        root = ET.fromstring(xml_content)

        result_parts = []
        self._process_element(root, result_parts, options)

        return options.line_separator.join(result_parts)

    def _process_element(
        self, elem: ET.Element, result: List[str], options: ExtractOptions
    ):
        tag = self._local_name(elem.tag)

        if tag == "p":
            para_text = self._extract_paragraph_text(elem, options)
            if para_text.strip() or options.include_empty_paragraphs:
                result.append(para_text)

        elif tag == "tbl":
            table_data = self._extract_table(elem)
            if table_data.rows:
                table_text = table_data.format(
                    options.table_style, options.table_delimiter
                )
                result.append(table_text)

        elif tag == "pic":
            marker = self._extract_image_marker(elem, options)
            if marker:
                result.append(marker)

        elif tag == "footNote":
            self._process_footnote(elem)

        elif tag == "endNote":
            self._process_endnote(elem)

        else:
            for child in elem:
                self._process_element(child, result, options)

    def _extract_paragraph_text(
        self, p_elem: ET.Element, options: ExtractOptions
    ) -> str:
        texts = []
        current_hyperlink_id = None
        hyperlink_text_parts = []
        hyperlink_url = None
        current_memo_id = None
        memo_text_parts = []

        for elem in p_elem.iter():
            tag = self._local_name(elem.tag)

            if tag == "t" and elem.text:
                if current_hyperlink_id:
                    hyperlink_text_parts.append(elem.text)
                if current_memo_id:
                    memo_text_parts.append(elem.text)
                texts.append(elem.text)

            elif tag == "pic":
                marker = self._extract_image_marker(elem, options)
                if marker:
                    texts.append(marker)

            elif tag == "footNote":
                note_number = self._process_footnote(elem)
                texts.append(f"[^{note_number}]")

            elif tag == "endNote":
                note_number = self._process_endnote(elem)
                texts.append(f"[^e{note_number}]")

            elif tag == "fieldBegin":
                field_type = elem.get("type", "")
                if field_type == "HYPERLINK":
                    current_hyperlink_id = elem.get("id")
                    hyperlink_url = self._extract_hyperlink_url(elem)
                    hyperlink_text_parts = []
                elif field_type == "MEMO":
                    current_memo_id = elem.get("id") or elem.get("name")
                    memo_text_parts = []

            elif tag == "fieldEnd":
                if current_hyperlink_id and hyperlink_url:
                    link_text = "".join(hyperlink_text_parts)
                    if link_text and hyperlink_url:
                        self._hyperlinks.append((link_text, hyperlink_url))
                current_hyperlink_id = None
                hyperlink_text_parts = []
                hyperlink_url = None

                if current_memo_id:
                    memo_text = "".join(memo_text_parts).strip()
                    if memo_text:
                        props = self._memo_properties.get(current_memo_id, {})
                        self._memos.append(
                            MemoData(
                                text=memo_text,
                                memo_id=current_memo_id,
                                width=int(props.get("width"))
                                if props.get("width")
                                else None,
                                fill_color=props.get("fillColor"),
                            )
                        )
                    current_memo_id = None
                    memo_text_parts = []

        return "".join(texts)

    def _extract_table(self, tbl_elem: ET.Element) -> TableData:
        rows = []

        for elem in tbl_elem.iter():
            tag = self._local_name(elem.tag)

            if tag == "tr":
                row_cells = self._extract_table_row(elem)
                if row_cells:
                    rows.append(row_cells)

        return TableData(rows=rows)

    def _extract_table_row(self, tr_elem: ET.Element) -> List[str]:
        cells = []

        for elem in tr_elem.iter():
            tag = self._local_name(elem.tag)

            if tag == "tc":
                cell_text = self._extract_cell_text(elem)
                cells.append(cell_text)

        return cells

    def _extract_cell_text(self, tc_elem: ET.Element) -> str:
        texts = []

        for elem in tc_elem.iter():
            tag = self._local_name(elem.tag)
            if tag == "t" and elem.text:
                texts.append(elem.text)

        return " ".join(texts).strip()

    def _extract_image_marker(
        self, pic_elem: ET.Element, options: ExtractOptions
    ) -> str:
        self._image_index += 1

        ref_id = None
        for elem in pic_elem.iter():
            tag = self._local_name(elem.tag)
            if tag == "img":
                ref_id = elem.get("binaryItemIdRef")
                break

        filename = None
        if ref_id:
            filename = self._get_image_filename(ref_id)

        return format_image_marker(options.image_marker, filename, self._image_index)

    def _process_footnote(self, footnote_elem: ET.Element) -> int:
        self._footnote_counter += 1
        number = int(footnote_elem.get("number", self._footnote_counter))
        text = self._extract_sublist_text(footnote_elem)
        self._footnotes.append(NoteData(note_type="footnote", number=number, text=text))
        return number

    def _process_endnote(self, endnote_elem: ET.Element) -> int:
        self._endnote_counter += 1
        number = int(endnote_elem.get("number", self._endnote_counter))
        text = self._extract_sublist_text(endnote_elem)
        self._endnotes.append(NoteData(note_type="endnote", number=number, text=text))
        return number

    def _extract_sublist_text(self, parent_elem: ET.Element) -> str:
        texts = []
        for elem in parent_elem.iter():
            tag = self._local_name(elem.tag)
            if tag == "t" and elem.text:
                texts.append(elem.text)
        return " ".join(texts).strip()

    def _extract_hyperlink_url(self, field_begin_elem: ET.Element) -> Optional[str]:
        for elem in field_begin_elem.iter():
            tag = self._local_name(elem.tag)
            if tag == "stringParam":
                raw_url = elem.text or elem.get("value", "")
                return self._clean_hyperlink_url(raw_url)
            elif tag == "param":
                value = elem.get("value", "")
                if value.startswith("http") or value.startswith("www"):
                    return self._clean_hyperlink_url(value)
        return None

    def _clean_hyperlink_url(self, url: str) -> str:
        url = url.replace("\\\\", "TEMP_BACKSLASH")
        url = url.replace("\\", "")
        url = url.replace("TEMP_BACKSLASH", "\\")
        if ";" in url:
            url = url.split(";")[0]
        return url


def extract_hwpx(
    filepath: Union[str, Path], options: Optional[ExtractOptions] = None
) -> Tuple[str, Optional[str]]:
    """
    Extract text from HWPX file.

    Returns:
        tuple: (text, error_message) - error is None on success
    """
    try:
        with HWPXReader(str(filepath)) as reader:
            if reader.is_encrypted():
                return "", "Password protected file"
            text = reader.extract_text(options)
            return text, None
    except Exception as e:
        return "", f"Extraction failed: {e}"
