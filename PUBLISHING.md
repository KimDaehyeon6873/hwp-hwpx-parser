# HWP-HWPX Parser 배포 가이드

이 문서는 hwp-hwpx-parser 라이브러리를 PyPI에 배포하는 방법을 설명합니다.

## 📋 배포 전 준비사항

### 1. 필수 파일들 확인
- [x] `pyproject.toml` - 프로젝트 설정
- [x] `README.md` - 프로젝트 설명
- [x] `LICENSE` - 라이선스 파일
- [x] `src/hwp_parser/jars/*.jar` - Java 라이브러리 파일들
- [x] `.gitignore` - Git 무시 파일
- [x] `MANIFEST.in` - 배포 파일 지정

### 2. PyPI 계정 준비
1. [PyPI](https://pypi.org/) 계정 생성
2. [TestPyPI](https://test.pypi.org/) 계정 준비 (테스트용)
3. API 토큰 생성 (Settings > API tokens)

### 3. 배포 도구 설치
```bash
pip install build twine
```

## 🚀 배포 방법

### 방법 1: 자동 배포 스크립트 사용 (권장)

#### TestPyPI에 테스트 배포
```bash
python scripts/publish.py --all
# 또는
python scripts/publish.py
```

#### 개별 단계 실행
```bash
# 1. 빌드 artifacts 정리
python scripts/publish.py --clean

# 2. 배포 전제 조건 확인
python scripts/publish.py --check

# 3. 패키지 빌드
python scripts/publish.py --build

# 4. 빌드된 패키지 테스트
python scripts/publish.py --test

# 5. TestPyPI 업로드
python scripts/publish.py --upload --test-pypi

# 6. 실제 PyPI 업로드
python scripts/publish.py --upload
```

### 방법 2: 수동 배포

#### 1. 빌드
```bash
# 빌드 artifacts 정리
rm -rf build/ dist/ *.egg-info/

# 패키지 빌드
python -m build
```

#### 2. 빌드 결과 확인
```bash
ls -la dist/
# hwp_hwpx_parser-0.1.0.tar.gz
# hwp_hwpx_parser-0.1.0-py3-none-any.whl
```

#### 3. TestPyPI에 업로드 (테스트)
```bash
python -m twine upload --repository testpypi dist/*
# 사용자명: __token__
# 비밀번호: pypi-xxx... (API 토큰)
```

#### 4. TestPyPI 설치 테스트
```bash
# 테스트 환경 생성
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# TestPyPI에서 설치
pip install -i https://test.pypi.org/simple/ hwp-hwpx-parser

# 테스트
python -c "from hwp_parser import HWPParser; print('설치 성공!')"
```

#### 5. 실제 PyPI에 업로드
```bash
python -m twine upload dist/*
```

## 📦 배포 파일 구조

```
dist/
├── hwp_hwpx_parser-0.1.0.tar.gz          # 소스 배포판
└── hwp_hwpx_parser-0.1.0-py3-none-any.whl  # wheel 배포판
```

## 🔍 배포 설정 상세

### pyproject.toml 설정
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "hwp-hwpx-parser"
version = "0.1.0"
dependencies = ["JPype1>=1.4.0"]

[tool.setuptools.package-data]
"hwp_parser" = ["jars/*.jar"]  # JAR 파일들 포함
```

### MANIFEST.in 설정
```
include README.md
include LICENSE
include jars/*.jar              # JAR 파일들
recursive-include src/hwp_parser *.jar
global-exclude *.pyc            # Python 캐시 파일 제외
prune ref/                      # 참조 폴더 제외
prune .git/                     # Git 파일들 제외
```

### .gitignore 설정
```
# 참조 파일들 (배포 제외)
ref/

# 빌드 artifacts
build/
dist/
*.egg-info/

# Python 캐시
__pycache__/
*.pyc
```

## 🧪 배포 테스트

### 1. 로컬 설치 테스트
```bash
# wheel 파일로 로컬 설치
pip install dist/hwp_hwpx_parser-0.1.0-py3-none-any.whl

# 기본 기능 테스트
python -c "
from hwp_parser import HWPParser, extract_text_from_hwp
print('✓ Import 성공')

parser = HWPParser()
print('✓ Parser 생성 성공')
"
```

### 2. JAR 파일 확인
```bash
python -c "
import hwp_parser
import os
jar_dir = os.path.join(os.path.dirname(hwp_parser.__file__), 'jars')
jars = [f for f in os.listdir(jar_dir) if f.endswith('.jar')]
print(f'✓ 포함된 JAR 파일들: {jars}')
"
```

## 🚨 문제 해결

### JAR 파일이 포함되지 않는 경우
```bash
# pyproject.toml에서 패키지 데이터 설정 확인
[tool.setuptools.package-data]
"hwp_parser" = ["jars/*.jar"]

# MANIFEST.in에 JAR 파일 포함 확인
include jars/*.jar
recursive-include src/hwp_parser *.jar
```

### 빌드 실패시
```bash
# 캐시 정리
rm -rf build/ dist/ *.egg-info/
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# 다시 빌드
python -m build
```

### 업로드 실패시
```bash
# API 토큰 확인
# __token__ 형식으로 사용자명 입력
# pypi-xxx... 형식으로 API 토큰 입력

# TestPyPI에 다시 시도
python -m twine upload --repository testpypi dist/*
```

## 📋 체크리스트

### 배포 전 확인사항
- [ ] 모든 테스트 통과 (`pytest`)
- [ ] 코드 포맷팅 완료 (`black`, `isort`)
- [ ] 타입 체크 통과 (`mypy`)
- [ ] 문서화 완료 (`README.md` 업데이트)
- [ ] 버전 번호 올바름
- [ ] JAR 파일들이 `src/hwp_parser/jars/`에 있음
- [ ] `.gitignore`에 `ref/` 폴더 제외됨

### TestPyPI 테스트 후 확인사항
- [ ] TestPyPI에서 설치 가능
- [ ] 기본 import 작동
- [ ] 주요 기능 작동
- [ ] JAR 파일들 정상 로드

### 실제 배포 전 최종 확인
- [ ] 버전 번호가 최종본
- [ ] README.md 내용 완전
- [ ] 라이선스 정보 정확
- [ ] 모든 테스트 통과

## 🔗 관련 링크

- [PyPI 프로젝트 페이지](https://pypi.org/project/hwp-hwpx-parser/)
- [TestPyPI 프로젝트 페이지](https://test.pypi.org/project/hwp-hwpx-parser/)
- [PyPI 배포 가이드](https://packaging.python.org/tutorials/packaging-projects/)
- [Twine 문서](https://twine.readthedocs.io/)

## 📞 지원

배포 관련 문제가 발생하면 다음을 확인하세요:
1. [PyPI 도움말](https://pypi.org/help/)
2. [Twine GitHub Issues](https://github.com/pypa/twine/issues)
3. 프로젝트 Issues 페이지
