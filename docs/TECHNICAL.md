# HWP/HWPX 파일 포맷 디코딩 기술 문서

본 문서는 HWP 5.0(바이너리) 및 HWPX(XML) 파일 포맷의 구조와 이를 파싱하여 텍스트, 표, 주석, 메모, 하이퍼링크 등의 데이터를 추출하는 기술적 세부 사항을 설명합니다.

## 1. 개요
한글 워드 프로세서 파일은 크게 두 가지 포맷으로 나뉩니다.
- **HWP 5.0**: OLE(Object Linking and Embedding) 화합물 파일 구조 기반의 바이너리 포맷.
- **HWPX**: ZIP 압축 아카이브 내에 XML 파일들이 구조적으로 배치된 포맷 (OWPML 표준).

---

## 2. HWPX 포맷 (ZIP/XML 기반)

HWPX 파일은 표준 ZIP 아카이브이며, 내부의 XML 파일들을 통해 문서 구조를 표현합니다.

### 2.1 파일 구조
주요 구성 요소는 다음과 같습니다.
- `META-INF/manifest.xml`: 파일 목록 및 암호화 여부 정보.
- `Contents/header.xml`: 문서의 메타데이터, 스타일, 바이너리 아이템(이미지) 맵, 메모 속성 등을 포함.
- `Contents/section{N}.xml`: 실제 문서 본문 내용이 담긴 파일 (0부터 시작).

### 2.2 주요 XML 요소 및 구조
- **네임스페이스**: 주로 `hp` (Hancom Office Office Open XML Word Processing Markup Language) 접두사를 사용합니다.
- **본문 구조**:
    - `<hp:p>`: 문단 (Paragraph).
    - `<hp:run>`: 문단 내의 실행 단위.
    - `<hp:t>`: 실제 텍스트 내용.
- **객체 및 특수 요소**:
    - `<hp:tbl>`: 표 (Table). 하위에 `<hp:tr>`(행), `<hp:tc>`(열) 구조를 가집니다.
    - `<hp:pic>`: 그림 (Picture). `<hp:img>` 요소의 `binaryItemIdRef` 속성을 통해 `header.xml`의 `binItem`과 연결됩니다.
- **주석 (Notes)**:
    - `<hp:footNote>`: 각주.
    - `<hp:endNote>`: 미주.
    - 내용 추출: 주석 요소 내부의 `<hp:subList>`를 탐색하여 텍스트를 수집합니다.
- **필드 (Fields)**:
    - `<hp:fieldBegin>` / `<hp:fieldEnd>`: 필드의 시작과 끝을 나타냅니다.
    - **하이퍼링크**: `type="HYPERLINK"` 속성을 가지며, `<hp:stringParam>` 또는 `<hp:param>` 요소에 URL이 포함됩니다. 시작과 끝 태그 사이의 텍스트가 표시 문자열입니다.
    - **메모**: `type="MEMO"` 속성을 가집니다. 메모의 본문 내용은 `fieldBegin` 내부의 `<hp:subList>`에 위치하며, 시작과 끝 태그 사이의 본문 텍스트가 메모가 참조하는 영역(`referenced_text`)이 됩니다.

---

## 3. HWP 5.0 포맷 (OLE Compound Binary)

HWP 5.0은 Microsoft의 OLE2 화합물 파일 형식을 사용합니다.

### 3.1 OLE 스트림 구조
- `FileHeader`: 파일 버전, 속성(압축 여부, 암호화 여부) 정보를 포함한 256바이트 스트림.
- `BodyText/Section{N}`: 실제 본문 데이터가 레코드 구조로 저장된 스트림.

### 3.2 레코드 구조 (Record Structure)
각 데이터는 가변 길이의 레코드 단위로 저장됩니다.
- **헤더 (4바이트)**:
    - Tag ID: 10비트 (0 ~ 1023)
    - Level: 10비트 (계층 구조 표현)
    - Size: 12비트 (데이터 크기. 0xFFF인 경우 다음 4바이트가 실제 크기)
- **주요 Tag ID**:
    - `HWPTAG_PARA_TEXT (67)`: 문단의 텍스트 데이터.
    - `HWPTAG_CTRL_HEADER (71)`: 표, 주석, 그림 등 컨트롤 객체의 속성.
    - `HWPTAG_LIST_HEADER (72)`: 표 셀, 각주/미주 등의 리스트 헤더.
    - `HWPTAG_SHAPE_COMPONENT (76)`: 도형/그림 컴포넌트 정보.
    - `HWPTAG_TABLE (77)`: 표의 구조 정보.
    - `HWPTAG_SHAPE_COMPONENT_PICTURE (85)`: 이미지 컴포넌트 (BinData 참조 포함).
    - `HWPTAG_MEMO_LIST (93)`: 메모 데이터 리스트.

### 3.3 텍스트 디코딩 및 제어 문자
텍스트는 기본적으로 **UTF-16LE** 인코딩을 사용합니다. 하지만 0~31 범위의 제어 문자가 특수한 의미를 가집니다.
- **제어 문자 코드**:
    - `9`: 탭 (Tab).
    - `11`: GSO (Graphic/Shape Object). 뒤에 8바이트의 확장 데이터가 따릅니다. 테이블과 이미지 모두 이 코드를 사용합니다.
    - `13`: 문단 끝 (하지만 레코드 단위로 문단이 구분되므로 보통 무시).
    - `17`: 필드 시작/끝 (각주, 미주, 하이퍼링크 등). 아래 3.3.1 참조.
    - `3`: 메모/필드 시작 (필드 텍스트의 시작).
    - `4`: 메모/필드 끝.

#### 3.3.1 확장 제어 문자 처리 (실제 구현)

제어 코드 17(CTRL_CHAR_FIELD)은 각주, 미주, 하이퍼링크 등의 필드를 나타냅니다.

**바이너리 구조:**
```
┌────────────────────────────────────────────────────────────┐
│  code (2B)  │  ctrl_id (4B)  │  extended_data (8B)   │ ... │
│   0x0011    │    "ftno"      │     (reserved)        │     │
└────────────────────────────────────────────────────────────┘
```

| 필드 | 크기 | 설명 |
|------|------|------|
| code | 2B | 제어 문자 코드 (0x0011 = 17) |
| ctrl_id | 4B | 제어 식별자 (리틀 엔디안 ASCII) |
| extended_data | 8B | 확장 데이터 (가비지 값 방지용 직렬화) |

**ctrl_id 종류:**
| ctrl_id (hex) | ASCII | 의미 |
|---------------|-------|------|
| 0x6E746F66 | `ftno` | 각주 (FootNote) |
| 0x6F6E6465 | `edno` | 미주 (EndNote) |
| 0x6B6E696C | `link` | 하이퍼링크 |

**본 파서의 구현:**
```python
EXTENDED_CTRL_EXT_SIZE = 12  # ctrl_id(4B) + extended_data(8B)
```

**처리 로직:**
```python
elif code == CTRL_CHAR_FIELD:  # code == 17
    if i + 4 <= len(record_data):
        ctrl_id = struct.unpack_from("<I", record_data, i)[0]
        
        if ctrl_id in (CTRL_ID_FOOTNOTE, CTRL_ID_ENDNOTE, CTRL_ID_HYPERLINK):
            # 알려진 제어문자: 12바이트 스킵
            i += EXTENDED_CTRL_EXT_SIZE
        elif self._is_valid_ctrl_id(ctrl_id):
            # 알 수 없지만 유효한 제어문자: 12바이트 스킵
            i += EXTENDED_CTRL_EXT_SIZE
        else:
            # 유효하지 않은 ctrl_id: 제어문자가 아님, 스킵하지 않음
            pass
```

**ctrl_id 유효성 검증:**

일부 HWP 파일에서 제어 코드 17(0x0011) 뒤에 실제로는 일반 텍스트가 오는 경우가 있습니다. 이를 구분하기 위해 ctrl_id의 4바이트가 모두 ASCII 출력 가능 문자(0x20~0x7E)인지 검사합니다:

```python
def _is_valid_ctrl_id(self, ctrl_id: int) -> bool:
    for j in range(4):
        byte = (ctrl_id >> (8 * j)) & 0xFF
        if not (0x20 <= byte <= 0x7E):
            return False
    return True
```

**실제 사례 (버그 수정 전후 비교):**

미주 마커 주변 텍스트 파싱 시 발생했던 문제:
```
수정 전: "지구[^2][^e1]리는"        (텍스트 손실)
수정 후: "지구[^2]와 외행성[^e1] 사이의 거리는"  (정상)
```

원인 분석:
- 위치 32에서 0x0011(제어 코드 17) 발견
- 다음 4바이트(ctrl_id)가 0x0020c640 → 한글 "와"(0xc640) 포함
- 0xc6은 ASCII 범위(0x20~0x7E)를 벗어남 → 유효하지 않은 ctrl_id
- 따라서 이것은 제어문자가 아니라 일반 텍스트 "와"로 처리해야 함

#### 3.3.2 공식 문서 vs 현재 구현 비교

**구조적으로 동일, 해석 방식이 다름:**

| 구분 | 공식 문서 | 현재 구현 |
|------|-----------|-----------|
| 상수 정의 | `CTRL_ID=4B`, `EXT_DATA=8B` (분리) | `EXTENDED_CTRL_EXT_SIZE=12B` (합산) |
| 스킵 계산 | `code(2) + ctrl_id(4) + ext(8) = 14B` | `code(2) + 12B = 14B` |
| 결과 | 동일 | 동일 |

**현재 구현만의 추가 사항 - `_is_valid_ctrl_id()` 검증:**

공식 문서에는 없지만, 실제 HWP 파일 파싱 중 발견된 엣지 케이스를 처리하기 위해 추가:

```python
# 공식 문서 방식 (단순)
if code == 17:
    i += 4 + 8  # 무조건 스킵

# 현재 구현 (방어적)
if code == 17:
    ctrl_id = read_4_bytes()
    if is_valid_ctrl_id(ctrl_id):  # ASCII 범위 체크
        i += 12  # 스킵
    else:
        pass  # 스킵 안함 - 일반 텍스트로 처리
```

**왜 이 검증이 필요한가?**

일부 HWP 파일에서 0x0011(제어 코드 17)이 실제 제어문자가 아닌 우연히 일치하는 바이트 패턴인 경우가 있음:

```
위치 32: 0x0011 (제어 코드 17처럼 보임)
위치 34: 0xc640 (한글 "와")  ← ctrl_id 자리에 한글이 있음
```

공식 문서대로만 구현하면 이 경우 12바이트를 스킵하여 텍스트 손실 발생.

### 3.4 GSO (Graphic/Shape Object) 처리
제어 코드 11은 모든 임베디드 객체(그림, 표, 도형 등)에 사용됩니다. 객체 타입을 구분하려면 후속 `CTRL_HEADER` 레코드를 확인해야 합니다.
- **CTRL_ID 구분**:
    - ` osg` (0x67736F20): 이미지/도형 GSO 컨테이너. `[IMAGE]` 마커 출력 대상.
    - ` lbt` (0x74626C20): 표(Table). `[IMAGE]` 마커 출력하지 않음.
- **이미지 마커 출력 로직**:
    1. 단락 텍스트에서 제어 코드 11 발견
    2. 해당 단락 이후의 `CTRL_HEADER` 레코드에서 CTRL_ID 확인
    3. CTRL_ID가 ` osg`인 경우에만 `[IMAGE]` 마커 출력
    4. BinData 스트림에 해당 이미지 파일이 존재하는지 추가 확인

### 3.5 컨트롤 식별자 (CTRL_ID) 및 추출 로직
`CTRL_HEADER` 레코드의 앞 4바이트는 컨트롤의 종류를 나타냅니다 (리틀 엔디안).
- `  nf` (각주), `  ne` (미주): 주석 텍스트는 해당 컨트롤 이후에 나타나는 `PARA_TEXT` 레코드들을 통해 추출합니다.
- `klh%` (하이퍼링크): URL 정보는 `CTRL_HEADER` 데이터 내에 인코딩되어 있으며, 표시 텍스트는 본문 내 제어 코드 3과 4 사이의 문자열입니다.
- `em%%` (메모): 메모의 참조 텍스트는 본문 내 코드 3과 4 사이의 문자열이며, 메모의 실제 내용은 파일 마지막 섹션 부근의 `HWPTAG_MEMO_LIST` 레코드에 저장됩니다.
- ` osg` (GSO 컨테이너): 이미지, 도형 등 그래픽 객체. 하위에 `SHAPE_COMPONENT` 및 `SHAPE_COMPONENT_PICTURE` 레코드가 따릅니다.
- ` lbt` (표): 표 객체. 하위에 `LIST_HEADER`와 셀 데이터가 따릅니다.

---

## 4. 공통 데이터 모델

파서는 두 포맷의 차이를 추상화하여 공통된 모델을 반환합니다.

### 4.1 ExtractResult
추출된 전체 결과를 담는 컨테이너입니다.
- `text`: 본문 텍스트. 주석과 메모는 마커 형식으로 삽입됩니다.
- `footnotes`: `NoteData` 리스트 (각주).
- `endnotes`: `NoteData` 리스트 (미주).
- `hyperlinks`: `(text, url)` 튜플 리스트.
- `memos`: `MemoData` 리스트.

### 4.2 마커 형식
텍스트 내에 삽입되는 위치 식별용 마커입니다.
- **각주**: `[^N]` (예: `[^1]`)
- **미주**: `[^eN]` (예: `[^e1]`)
- **메모**: `[MEMO:N]` (예: `[MEMO:1]`)

---

## 5. 주요 구현 세부 사항

### 5.1 유니코드 유효 범위 검증
바이너리 포맷 파싱 시, 잘못된 제어 문자로 인해 텍스트가 오염되는 것을 방지하기 위해 유효한 유니코드 범위를 체크합니다.
- 한글 음절: `0xAC00 ~ 0xD7AF`
- 한글 자모: `0x1100 ~ 0x11FF`, `0x3130 ~ 0x318F`
- 기본 라틴 및 특수 기호 등 포함.

### 5.2 표(Table) 추출 로직
1. `HWPTAG_TABLE` 레코드에서 행(Rows)과 열(Cols) 수를 파악합니다.
2. 이후 나타나는 `HWPTAG_LIST_HEADER` 레코드를 통해 각 셀의 시작을 감지합니다.
3. 각 셀 내의 `HWPTAG_PARA_TEXT`를 수집하여 셀 텍스트를 구성합니다.
4. 추출된 데이터를 `TableData` 모델로 변환하여 Markdown, CSV 등의 형식으로 출력할 수 있습니다.

### 5.3 중첩 필드 및 제어 코드 처리
HWP 파일은 필드 내에 또 다른 필드가 존재하거나, 제어 코드가 복합적으로 나타날 수 있습니다. 파서는 상태 머신(State Machine) 또는 큐(Queue)를 사용하여 현재 처리 중인 하이퍼링크나 메모의 상태를 관리하며 데이터를 정확히 매칭합니다.

---

## 6. 코드 예시 (Python)

```python
from hwp_hwpx_parser import Reader

# 파일 읽기 (포맷 자동 감지)
with Reader("document.hwp") as reader:
    # 전체 텍스트 및 주석 추출
    result = reader.extract_text_with_notes()
    print(f"본문: {result.text}")
    
    # 각주 확인
    for note in result.footnotes:
        print(f"각주 [{note.number}]: {note.text}")
        
    # 표를 Markdown 형식으로 변환
    for table in reader.tables:
        print(table.to_markdown())
        
    # 메모 추출
    for memo in reader.get_memos():
        print(f"메모: {memo.text} (참조: {memo.referenced_text})")
```
