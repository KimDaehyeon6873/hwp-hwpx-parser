# HWP-HWPX Parser 배포 가이드

이 문서는 hwp-hwpx-parser 라이브러리를 PyPI에 배포하는 방법을 설명합니다.

## 버전 동기화 (중요)

**hwp-hwpx-parser**와 **hwp-hwpx-editor**는 항상 동일한 버전으로 배포합니다.

```
parser v0.1.4  ←→  editor v0.1.4
```

릴리스 순서:
1. **parser 먼저 배포** (`git tag v0.1.4` → push)
2. **editor 동일 버전 배포** (`git tag v0.1.4` → push)

## 버전 관리

이 프로젝트는 **setuptools-scm**을 사용하여 git tag 기반으로 버전을 자동 관리합니다.

- 버전은 `pyproject.toml`이나 코드에 하드코딩되지 않음
- git tag가 버전이 됨 (예: `v0.1.4` → 버전 `0.1.4`)
- 개발 중에는 자동으로 dev 버전 생성 (예: `0.1.5.dev3`)

## 배포 방법

### 방법 1: GitHub Actions 자동 배포 (권장)

git tag를 push하면 GitHub Actions가 자동으로 테스트 및 PyPI 배포를 수행합니다.

```bash
# 1. 변경사항 커밋
git add .
git commit -m "Release v0.1.4"

# 2. 태그 생성
git tag v0.1.4

# 3. 태그 푸시 (자동 배포 트리거)
git push origin main
git push origin v0.1.4
```

### GitHub 설정 (최초 1회)

#### Trusted Publisher 설정 (권장)

PyPI의 Trusted Publisher를 사용하면 API 토큰 없이 안전하게 배포할 수 있습니다.

1. [PyPI](https://pypi.org/) 로그인
2. 프로젝트 → Settings → Publishing
3. "Add a new pending publisher" 클릭
4. 다음 정보 입력:
   - Owner: `KimDaehyeon6873`
   - Repository: `hwp-hwpx-parser`
   - Workflow name: `publish.yml`
   - Environment: `pypi`

#### 또는 API Token 방식

1. PyPI에서 API token 생성
2. GitHub → Settings → Secrets and variables → Actions
3. `PYPI_API_TOKEN` 시크릿 추가
4. `.github/workflows/publish.yml` 수정:

```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    password: ${{ secrets.PYPI_API_TOKEN }}
```

### 방법 2: 수동 배포

로컬에서 직접 배포해야 하는 경우:

```bash
# 1. 빌드 도구 설치
pip install build twine

# 2. 빌드 artifacts 정리
rm -rf build/ dist/ src/*.egg-info/

# 3. 패키지 빌드
python -m build

# 4. PyPI 업로드
python -m twine upload dist/*
```

## 배포 워크플로우

```
코드 작성 → commit → push
    ↓
릴리스 준비 완료
    ↓
git tag v0.1.4 → git push origin v0.1.4
    ↓
GitHub Actions 자동 실행
    ↓
테스트 (Python 3.9, 3.10, 3.11, 3.12)
    ↓
PyPI 자동 배포
```

## 버전 확인

```python
# 설치된 패키지 버전 확인
import hwp_hwpx_parser
print(hwp_hwpx_parser.__version__)
```

```bash
# CLI에서 확인
pip show hwp-hwpx-parser
```

## 프로젝트 구조

```
pyproject.toml          # setuptools-scm 설정 포함
src/
  hwp_hwpx_parser/
    __init__.py         # importlib.metadata로 버전 읽기
    ...
.github/
  workflows/
    publish.yml         # 자동 배포 워크플로우
```

### pyproject.toml 설정

```toml
[build-system]
requires = ["setuptools>=61.0", "setuptools-scm>=8.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "hwp-hwpx-parser"
dynamic = ["version"]  # 버전은 git tag에서 자동 추출

[tool.setuptools_scm]
version_scheme = "guess-next-dev"
local_scheme = "no-local-version"
```

### __init__.py 버전 코드

```python
try:
    from importlib.metadata import version
    __version__ = version("hwp-hwpx-parser")
except Exception:
    __version__ = "0.0.0"
```

## 체크리스트

### 배포 전 확인사항
- [ ] 모든 테스트 통과 (`pytest`)
- [ ] README.md 업데이트 (필요시)
- [ ] CHANGELOG.md 업데이트 (필요시)

### 릴리스 절차
- [ ] 변경사항 커밋 완료
- [ ] main 브랜치에 push 완료
- [ ] git tag 생성 (`git tag vX.Y.Z`)
- [ ] tag push (`git push origin vX.Y.Z`)
- [ ] GitHub Actions 성공 확인
- [ ] PyPI에서 새 버전 확인

## 관련 링크

- [PyPI 프로젝트 페이지](https://pypi.org/project/hwp-hwpx-parser/)
- [GitHub Actions 워크플로우](.github/workflows/publish.yml)
- [setuptools-scm 문서](https://setuptools-scm.readthedocs.io/)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
