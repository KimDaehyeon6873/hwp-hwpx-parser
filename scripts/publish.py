#!/usr/bin/env python3
"""
HWP-HWPX Parser 배포 스크립트

PyPI 배포를 위한 빌드 및 업로드 자동화 스크립트입니다.
"""

import subprocess
import sys
import os
from pathlib import Path
import argparse
import shutil


def run_command(cmd, cwd=None, check=True):
    """명령어 실행 헬퍼 함수"""
    print(f"실행: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"오류 발생: {result.stderr}")
        sys.exit(1)
    return result


def clean_build_artifacts():
    """빌드 artifacts 정리"""
    print("빌드 artifacts 정리 중...")
    dirs_to_remove = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_remove:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  제거됨: {path}")
            elif path.is_file():
                path.unlink()
                print(f"  제거됨: {path}")


def check_prerequisites():
    """배포 전제 조건 확인"""
    print("배포 전제 조건 확인 중...")

    # Python 버전 확인
    if sys.version_info < (3, 8):
        print("오류: Python 3.8 이상이 필요합니다.")
        sys.exit(1)
    print(f"  ✓ Python 버전: {sys.version}")

    # 필수 파일들 확인
    required_files = [
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "src/hwp_parser/__init__.py"
    ]

    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"오류: 필수 파일이 없습니다: {file_path}")
            sys.exit(1)
    print("  ✓ 필수 파일들 존재 확인")

    # JAR 파일들 확인
    jar_dir = Path("src/hwp_parser/jars")
    if not jar_dir.exists():
        print("오류: JAR 파일 디렉토리가 없습니다")
        sys.exit(1)

    jar_files = list(jar_dir.glob("*.jar"))
    if not jar_files:
        print("오류: JAR 파일들이 없습니다")
        sys.exit(1)
    print(f"  ✓ JAR 파일들: {len(jar_files)}개 발견")

    # twine 설치 확인
    try:
        run_command([sys.executable, "-m", "pip", "show", "twine"])
        print("  ✓ twine 설치됨")
    except:
        print("오류: twine이 설치되지 않았습니다. 설치하세요: pip install twine")
        sys.exit(1)

    # build 설치 확인
    try:
        run_command([sys.executable, "-m", "pip", "show", "build"])
        print("  ✓ build 설치됨")
    except:
        print("오류: build가 설치되지 않았습니다. 설치하세요: pip install build")
        sys.exit(1)


def build_package():
    """패키지 빌드"""
    print("패키지 빌드 중...")
    run_command([sys.executable, "-m", "build"])


def test_package():
    """빌드된 패키지 테스트"""
    print("빌드된 패키지 테스트 중...")

    # wheel 파일 찾기
    wheel_files = list(Path("dist").glob("*.whl"))
    if not wheel_files:
        print("오류: 빌드된 wheel 파일을 찾을 수 없습니다")
        sys.exit(1)

    wheel_file = wheel_files[0]
    print(f"  테스트할 wheel 파일: {wheel_file}")

    # 임시 가상환경에서 설치 테스트
    import tempfile
    import venv

    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = Path(temp_dir) / "test_venv"

        # 가상환경 생성
        venv.create(venv_path, with_pip=True)

        # pip 경로
        pip_path = venv_path / "bin" / "pip"
        if os.name == 'nt':  # Windows
            pip_path = venv_path / "Scripts" / "pip.exe"

        # 패키지 설치
        run_command([str(pip_path), "install", str(wheel_file)])

        # 기본 import 테스트
        python_path = venv_path / "bin" / "python"
        if os.name == 'nt':
            python_path = venv_path / "Scripts" / "python.exe"

        test_script = """
import sys
sys.path.insert(0, '.')

try:
    from hwp_parser import HWPParser, extract_text_from_hwp
    print("SUCCESS: 패키지 import 성공")
except ImportError as e:
    print(f"FAILED: 패키지 import 실패 - {e}")
    sys.exit(1)
"""

        with open(Path(temp_dir) / "test_import.py", "w") as f:
            f.write(test_script)

        result = run_command([str(python_path), str(Path(temp_dir) / "test_import.py")])
        if "SUCCESS" in result.stdout:
            print("  ✓ 패키지 설치 및 import 테스트 통과")
        else:
            print("  ✗ 패키지 설치 및 import 테스트 실패")
            print(result.stdout)
            sys.exit(1)


def upload_to_pypi(test_pypi=False):
    """PyPI 업로드"""
    target = "TestPyPI" if test_pypi else "PyPI"
    print(f"{target}에 업로드 중...")

    cmd = [sys.executable, "-m", "twine", "upload"]
    if test_pypi:
        cmd.extend(["--repository", "testpypi"])

    # dist 폴더의 모든 파일 업로드
    cmd.extend(["dist/*"])

    print(f"다음 명령어 실행: {' '.join(cmd)}")
    print("API 토큰 또는 사용자 인증 정보가 필요합니다.")

    # 실제 업로드는 사용자가 직접 확인하도록 함
    print(f"\n{target} 업로드를 위해 다음 명령어를 실행하세요:")
    print(f"  {' '.join(cmd)}")
    print("\n또는 이 스크립트에 --upload 옵션을 사용하세요.")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="HWP-HWPX Parser 배포 스크립트")
    parser.add_argument("--clean", action="store_true", help="빌드 artifacts 정리")
    parser.add_argument("--check", action="store_true", help="배포 전제 조건 확인")
    parser.add_argument("--build", action="store_true", help="패키지 빌드")
    parser.add_argument("--test", action="store_true", help="빌드된 패키지 테스트")
    parser.add_argument("--upload", action="store_true", help="PyPI 업로드")
    parser.add_argument("--test-pypi", action="store_true", help="TestPyPI에 업로드")
    parser.add_argument("--all", action="store_true", help="전체 배포 과정 실행 (TestPyPI)")

    args = parser.parse_args()

    # 기본 동작: 모든 단계 실행
    if args.all or len(sys.argv) == 1:
        print("전체 배포 과정 실행 (TestPyPI)...")
        clean_build_artifacts()
        check_prerequisites()
        build_package()
        test_package()
        upload_to_pypi(test_pypi=True)
        return

    # 개별 단계 실행
    if args.clean:
        clean_build_artifacts()

    if args.check:
        check_prerequisites()

    if args.build:
        build_package()

    if args.test:
        test_package()

    if args.upload:
        upload_to_pypi(test_pypi=args.test_pypi)


if __name__ == "__main__":
    main()
