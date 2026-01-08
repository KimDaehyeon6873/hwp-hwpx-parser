#!/usr/bin/env python3
"""
Java 라이브러리 JAR 파일들을 Maven Central에서 다운로드합니다.
"""

import os
import urllib.request
import urllib.error
import ssl
from pathlib import Path

# JAR 파일 정보
JARS = {
    "hwplib": {
        "group_id": "kr.dogfoot",
        "artifact_id": "hwplib",
        "version": "1.1.10",
        "filename": "hwplib-1.1.10.jar"
    },
    "hwpxlib": {
        "group_id": "kr.dogfoot",
        "artifact_id": "hwpxlib",
        "version": "1.0.8",
        "filename": "hwpxlib-1.0.8.jar"
    },
    # POI 라이브러리 (hwplib의존성)
    "poi": {
        "group_id": "org.apache.poi",
        "artifact_id": "poi",
        "version": "3.9",
        "filename": "poi-3.9.jar"
    },
    "poi-ooxml": {
        "group_id": "org.apache.poi",
        "artifact_id": "poi-ooxml",
        "version": "3.9",
        "filename": "poi-ooxml-3.9.jar"
    },
    "poi-scratchpad": {
        "group_id": "org.apache.poi",
        "artifact_id": "poi-scratchpad",
        "version": "3.9",
        "filename": "poi-scratchpad-3.9.jar"
    }
}

def download_jar(jar_info, output_dir):
    """Maven Central에서 JAR 파일을 다운로드합니다."""
    group_path = jar_info["group_id"].replace(".", "/")
    artifact_id = jar_info["artifact_id"]
    version = jar_info["version"]
    filename = jar_info["filename"]

    # Maven Central URL 생성
    url = f"https://repo1.maven.org/maven2/{group_path}/{artifact_id}/{version}/{filename}"

    output_path = output_dir / filename

    print(f"Downloading {filename}...")
    try:
        # SSL 검증 비활성화 (개발 환경용)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(url, context=ctx) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())

        print(f"Downloaded {filename} successfully")
        return True
    except urllib.error.HTTPError as e:
        print(f"Failed to download {filename}: {e}")
        return False
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False

def main():
    """메인 함수"""
    jars_dir = Path("jars")
    jars_dir.mkdir(exist_ok=True)

    print("Downloading Java libraries...")

    success_count = 0
    for jar_name, jar_info in JARS.items():
        if download_jar(jar_info, jars_dir):
            success_count += 1

    print(f"\nDownloaded {success_count}/{len(JARS)} JAR files")

    if success_count < len(JARS):
        print("Some JAR files failed to download. Please check your internet connection.")
        return 1

    print("All JAR files downloaded successfully!")
    return 0

if __name__ == "__main__":
    exit(main())
