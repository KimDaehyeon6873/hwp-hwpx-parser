# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-01-08

### Fixed
- HWP5 `[IMAGE]` 마커가 테이블에도 잘못 출력되던 문제 수정
  - GSO 컨트롤 타입 구분: ` osg` (이미지) vs ` lbt` (테이블)
  - `_has_image_gso()` 메서드 추가로 이미지 GSO만 정확히 식별
- HWP5 메모 추출 시 고정 레코드 수(50개) 제한 제거
  - level 기반 종료 조건으로 긴 메모도 완전히 추출
- HWP5 메모 내용이 본문에 중복 출력되던 문제 수정
  - `HWPTAG_MEMO_LIST` 섹션 스킵 로직 추가

### Changed
- 기술 문서(TECHNICAL.md) GSO 처리 로직 상세 설명 추가
  - CTRL_ID 구분 (` osg`, ` lbt`)
  - HWPTAG_SHAPE_COMPONENT, HWPTAG_SHAPE_COMPONENT_PICTURE 설명

---

## [Unreleased]

### Added
- Fast Layer 메모(Memo) 추출 기능
  - `get_memos_fast()`: HWP 및 HWPX 메모 추출 (통합 지원)
  - `MemoData` 데이터 클래스
  - HWP5 HWPTAG_MEMO_LIST (Tag 93) 파싱
  - HWPX `<hp:fieldBegin type="MEMO">` 파싱
  - ExtractResult에 `memos` 필드 추가
- Fast Layer 각주/미주/하이퍼링크 추출 기능
  - `extract_text_with_notes_fast()`: 텍스트 + 각주/미주/하이퍼링크/메모 통합 추출
  - `get_footnotes_fast()`: 각주 목록 추출
  - `get_endnotes_fast()`: 미주 목록 추출
  - `get_hyperlinks_fast()`: 하이퍼링크 목록 추출
- `NoteData`, `HyperlinkData`, `MemoData`, `ExtractResult` 데이터 클래스
- HWP5 각주(`fn  `)/미주(`en  `)/하이퍼링크(`%hlk`) ctrl_id 파싱
- HWPX `<hp:footNote>`, `<hp:endNote>`, `<hp:fieldBegin type="HYPERLINK">` 파싱
- 단위 테스트 41개 추가 (`test_fast_notes.py`, `test_document_fast.py`)

### Fixed
- HWP5 각주/미주 중복 추출 문제 해결 (전역 카운터 사용)
- HWPX 하이퍼링크 URL escape 문자 정리 (`https\\://` → `https://`)
- `src/hwp_parser/hwp/control.py`: `from enum import Enum` 누락 수정

---

## [0.1.0] - 2025-01-XX

### Added

#### Fast Layer (순수 Python - JVM 불필요)
- `Document(file_path, fast_mode=True)`: Java 없이 문서 열기
- `extract_text_fast()`: 순수 Python으로 텍스트 추출
- HWP5 바이너리 포맷 직접 파싱 (olefile 기반)
- HWPX XML 포맷 파싱 (zipfile + xml.etree 기반)
- 암호화 파일 자동 감지

#### JVM 모드 (전체 기능)

##### HWP 파일 지원
- 파일 읽기/쓰기
- 텍스트 추출 (3가지 옵션: 메인 문단, 컨트롤 삽입, 컨트롤 추가)
- 필드 텍스트 조작 (`get_field_text`, `set_field_text`, `get_all_field_text`)
- 컨트롤 찾기 및 필터링 (`find_controls`, `find_controls_by_type`)
- 표 조작 (셀 병합, 행 삭제, 표 정보 조회)
- 표 텍스트 추출 (`extract_table_text`, `get_table_as_markdown`, `get_table_as_csv`)
- 이미지 삽입 (`insert_image`)
- 하이퍼링크 삽입 (`insert_hyperlink`)
- 주석(숨은 설명) 관리 (`find_comments`, `get_comment_text`, `create_comment`)
- 빈 파일 생성 (`create_blank`)

##### HWPX 파일 지원
- 파일 읽기/쓰기
- 텍스트 추출 (3가지 옵션 + 사용자 정의 마크)
- 객체 찾기 (`find_tables`, `find_images`, `find_paragraphs`)
- 메모 속성 관리 (`find_memo_properties`, `get_memo_info`, `create_memo_property`)
- 빈 파일 생성

##### 통합 API
- `HWPParser` 클래스: 통합 파서
- `Document` 클래스: 통합 문서 객체
- `find_all(tag)`: Rust hwp-rs 스타일 객체 검색
- 자동 파일 타입 감지 (확장자 기반)
- 컨텍스트 매니저 지원 (`with` 문)
- extract-hwp 호환 API (`extract_text_from_hwp`, `is_hwp_file_password_protected`)

##### 예외 처리
- `HWPParserError`: 기본 예외
- `JVMNotStartedError`: JVM 미시작
- `FileNotFoundError`: 파일 없음
- `UnsupportedFileFormatError`: 미지원 포맷
- `ParsingError`: 파싱 오류
- `WritingError`: 쓰기 오류

### Technical Details
- Python 3.8+ 지원
- Java 7+ 지원 (JVM 모드)
- JPype1 기반 Java-Python 통합
- hwplib 1.1.10 기반 HWP 처리
- hwpxlib 1.0.8 기반 HWPX 처리
- Apache POI 3.9 지원
- 크로스 플랫폼 (Windows, macOS, Linux)

---

## Version History

| 버전 | 날짜 | 주요 변경 |
|------|------|-----------|
| 0.1.0 | 2025-01-XX | 최초 릴리스 |

---

**마이그레이션 가이드**: v0.1.0이 첫 공개 버전이므로 별도의 마이그레이션이 필요하지 않습니다.
