# HWP-HWPX Parser

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/hwp-hwpx-parser.svg)](https://pypi.org/project/hwp-hwpx-parser/)
[![No JVM Required](https://img.shields.io/badge/JVM-Not%20Required-green.svg)](#)

**순수 Python HWP/HWPX 파서** - JVM 없이 텍스트, 표, 각주, 미주, 메모 추출

## 특징

- **JVM 불필요**: 순수 Python 구현, Java 설치 없이 바로 사용
- **경량**: 최소 의존성 (`olefile`만 필요)
- **빠른 시작**: `pip install hwp-hwpx-parser`로 즉시 사용
- **통합 API**: HWP/HWPX 파일을 동일한 인터페이스로 처리
- **풍부한 추출**: 텍스트, 표, 각주, 미주, 하이퍼링크, 메모 지원

## 설치

```bash
pip install hwp-hwpx-parser
```

## 빠른 시작

```python
from hwp_hwpx_parser import Reader

# 컨텍스트 매니저 사용 (권장)
with Reader("document.hwp") as r:
    print(r.text)                    # 본문 텍스트
    print(r.tables)                  # 표 목록
    print(r.get_memos())             # 메모 목록

# HWPX 파일도 동일하게 사용
with Reader("document.hwpx") as r:
    print(r.text)
```

## API 레퍼런스

### Reader (통합 리더)

```python
from hwp_hwpx_parser import Reader

with Reader("document.hwp") as r:
    # 기본 속성
    r.text                      # 본문 텍스트 (str)
    r.tables                    # 표 목록 (List[TableData])
    r.file_type                 # 파일 타입 (FileType.HWP5 또는 FileType.HWPX)
    r.is_valid                  # 유효한 파일인지 (bool)
    r.is_encrypted              # 암호화 여부 (bool)
    
    # 메서드
    r.extract_text()                    # 텍스트 추출
    r.extract_text_with_notes()         # 텍스트 + 각주/미주/링크/메모 통합 추출
    r.get_tables()                      # 표 목록
    r.get_memos()                       # 메모 목록
    r.get_tables_as_markdown()          # 표를 마크다운 형식으로
    r.get_tables_as_csv()               # 표를 CSV 형식으로
```

### 개별 리더

```python
from hwp_hwpx_parser import HWP5Reader, HWPXReader

# HWP 5.0 파일 전용
reader = HWP5Reader("document.hwp")

# HWPX 파일 전용
reader = HWPXReader("document.hwpx")
```

### 편의 함수

```python
from hwp_hwpx_parser import read, extract_hwp5, extract_hwpx

# read() - Reader 인스턴스 반환
reader = read("document.hwp")
print(reader.text)
reader.close()

# extract_hwp5() - HWP 텍스트 바로 추출
text = extract_hwp5("document.hwp")

# extract_hwpx() - HWPX 텍스트 바로 추출
text = extract_hwpx("document.hwpx")
```

### 데이터 모델

```python
from hwp_hwpx_parser import (
    ExtractOptions,    # 추출 옵션
    TableData,         # 표 데이터
    TableStyle,        # 표 스타일 (INLINE, MARKDOWN, CSV)
    NoteData,          # 각주/미주 데이터
    HyperlinkData,     # 하이퍼링크 데이터
    MemoData,          # 메모 데이터
    ExtractResult,     # 통합 추출 결과
)

# TableData 사용
table = reader.tables[0]
print(table.rows)           # 2D 리스트: [[cell1, cell2], ...]
print(table.row_count)      # 행 수
print(table.col_count)      # 열 수
print(table.to_markdown())  # 마크다운 변환
print(table.to_csv())       # CSV 변환

# ExtractResult 사용
result = reader.extract_text_with_notes()
print(result.text)          # 본문 (각주는 [^1], 미주는 [^e1]로 표시)
print(result.footnotes)     # List[NoteData]
print(result.endnotes)      # List[NoteData]
print(result.hyperlinks)    # List[Tuple[str, str]]
print(result.memos)         # List[MemoData]
```

### 추출 옵션

```python
from hwp_hwpx_parser import ExtractOptions, TableStyle, ImageMarkerStyle

options = ExtractOptions(
    table_style=TableStyle.MARKDOWN,        # 표 출력 스타일
    table_delimiter=",",                    # CSV 구분자
    image_marker=ImageMarkerStyle.SIMPLE,   # 이미지 마커 스타일
    paragraph_separator="\n\n",             # 문단 구분자
    line_separator="\n",                    # 줄 구분자
    include_empty_paragraphs=False,         # 빈 문단 포함 여부
)

text = reader.extract_text(options)
```

## 지원 기능

| 기능 | HWP | HWPX |
|------|-----|------|
| 텍스트 추출 | ✅ | ✅ |
| 표 추출 | ✅ | ✅ |
| 각주 추출 | ✅ | ✅ |
| 미주 추출 | ✅ | ✅ |
| 하이퍼링크 추출 | ✅ | ✅ |
| 메모 추출 | ✅ | ✅ |
| 암호화 파일 감지 | ✅ | ✅ |

## 문서 편집이 필요하다면

이 패키지는 **읽기 전용**입니다. 문서 편집(텍스트 수정, 표 조작 등)이 필요하면 `hwp-hwpx-editor`를 설치하세요:

```bash
pip install hwp-hwpx-editor
```

`hwp-hwpx-editor`는 이 패키지를 기반으로 Java 라이브러리를 활용한 편집 기능을 제공합니다.

## 요구사항

- **Python**: 3.8 이상
- **의존성**: `olefile>=0.46` (자동 설치)
- **Java**: 불필요

## 라이선스

Apache License 2.0

## 관련 프로젝트

- [hwp-hwpx-editor](https://github.com/KimDaehyeon6873/hwp-hwpx-editor) - HWP/HWPX 문서 편집 라이브러리
- [hwplib](https://github.com/neolord0/hwplib) - Java HWP 라이브러리 (hwp-hwpx-editor에서 사용)
- [hwpxlib](https://github.com/neolord0/hwpxlib) - Java HWPX 라이브러리 (hwp-hwpx-editor에서 사용)
