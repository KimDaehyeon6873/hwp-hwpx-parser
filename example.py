#!/usr/bin/env python3
"""
HWP-HWPX Parser 종합 사용 예제
"""

import sys
import os

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """메인 함수"""
    print("🎯 HWP-HWPX Parser - 종합 예제")
    print("=" * 50)

    try:
        # 기본 모듈들 import
        print("\n📦 라이브러리 구조 확인 중...")

        # JPype 확인
        try:
            import jpype
            jpype_available = True
            print("✓ JPype1 라이브러리 사용 가능")
        except ImportError:
            jpype_available = False
            print("⚠ JPype1 라이브러리 없음 (pip install JPype1)")

        # 핵심 모듈들 import
        from hwp_parser.core.exceptions import HWPParserError, FileNotFoundError
        from hwp_parser.document import DocumentType
        from hwp_parser import HWPParser

        print("✓ 기본 모듈들 import 성공")
        print(f"✓ 지원 문서 타입: {[dt.value for dt in DocumentType]}")

        # JAR 파일 확인
        from pathlib import Path
        jars_dir = Path("jars")
        if jars_dir.exists():
            jar_files = list(jars_dir.glob("*.jar"))
            print(f"✓ Java 라이브러리 파일들 발견: {len(jar_files)}개")
            for jar in jar_files:
                print(f"  - {jar.name}")
        else:
            print("⚠ Java 라이브러리 디렉토리 없음")

        print("\n🚀 사용 예제들")
        print("-" * 30)

        # 파서 생성
        parser = HWPParser()
        print("✓ HWPParser 인스턴스 생성")

        # Rust hwp-rs 스타일 API 데모
        print("\n🆕 Rust hwp-rs 스타일 API:")
        try:
            # Rust 스타일로 파일 읽기
            doc = parser('test.hwp')  # parser('file.hwp') 호출
            print("✓ Rust 스타일 파일 읽기 성공")

            # 속성 접근
            print(f"  문서 버전: {doc.version}")
            print(f"  섹션 수: {len(doc.sections)}")
            print(f"  바이너리 파일 수: {len(doc.bin_data)}")

            # find_all 메소드
            paragraphs = doc.find_all('paragraph')
            tables = doc.find_all('table')
            print(f"  문단 수: {len(paragraphs)}")
            print(f"  표 수: {len(tables)}")

            doc.close()
        except Exception as e:
            print(f"⚠️ Rust 스타일 API 테스트 실패 (테스트 파일 없음): {e}")

        # extract-hwp 스타일 간단한 텍스트 추출
        print("\n📄 extract-hwp 스타일 간단한 API:")
        try:
            from hwp_parser import extract_text_from_hwp, is_hwp_file_password_protected

            text, error = extract_text_from_hwp("test.hwp")
            if error is None:
                print(f"✓ 간단한 텍스트 추출 성공: {len(text)}자")
                print(f"  내용 미리보기: {text[:100]}...")
            else:
                print(f"⚠️ 텍스트 추출 실패: {error}")

            # 암호화 파일 감지
            if is_hwp_file_password_protected("test.hwp"):
                print("✓ 암호화 파일 감지됨")
            else:
                print("✓ 일반 파일 (암호화되지 않음)")

        except Exception as e:
            print(f"⚠️ extract-hwp 스타일 API 테스트 실패: {e}")

        # 표 텍스트 추출 데모
        print("\n📊 표 텍스트 추출 데모:")
        try:
            doc = parser('test.hwp')
            tables = doc.find_all('table')

            if tables:
                table_control = tables[0]  # 첫 번째 표
                print("✓ 표를 찾았습니다!")

                # 표 정보 확인
                table_info = doc.get_table_info(table_control)
                print(f"  표 크기: {table_info.get('row_count', 0)}행 x {table_info.get('column_count', 0)}열")

                # 셀별 텍스트 추출
                table_texts = doc.extract_table_text(table_control)
                print(f"  추출된 셀 텍스트: {len(table_texts)}행")

                # 마크다운 변환
                markdown = doc.get_table_as_markdown(table_control)
                if markdown:
                    print("  마크다운 변환 성공!")
                    print("    " + "\n    ".join(markdown.split("\n")[:3]))

                # CSV 변환
                csv_data = doc.get_table_as_csv(table_control)
                if csv_data:
                    print("  CSV 변환 성공!")
                    print("    " + "\n    ".join(csv_data.split("\n")[:2]))

            else:
                print("⚠️ 테스트 파일에 표가 없거나 찾을 수 없습니다.")

            doc.close()

        except Exception as e:
            print(f"⚠️ 표 텍스트 추출 데모 실패: {e}")

        # 빈 문서 생성 예제
        print("\n📄 빈 문서 생성 예제:")
        try:
            hwp_doc = parser.create_blank(DocumentType.HWP)
            hwpx_doc = parser.create_blank(DocumentType.HWPX)
            print("✓ 빈 HWP 문서 생성 성공")
            print("✓ 빈 HWPX 문서 생성 성공")

            # 텍스트 추출
            hwp_text = hwp_doc.extract_text()
            hwpx_text = hwpx_doc.extract_text()
            print(f"✓ HWP 빈 문서 텍스트 길이: {len(hwp_text)}")
            print(f"✓ HWPX 빈 문서 텍스트 길이: {len(hwpx_text)}")

            hwp_doc.close()
            hwpx_doc.close()

        except Exception as e:
            print(f"⚠ 빈 문서 생성 중 오류: {e}")

        # HWP 기능 데모 (실제 파일이 있으면)
        hwp_path = Path("tests/data/blank.hwp")
        if hwp_path.exists():
            print(f"\n📖 HWP 파일 읽기 예제 ({hwp_path.name}):")
            try:
                with parser.read(hwp_path) as doc:
                    text = doc.extract_text()
                    print(f"✓ 텍스트 추출 성공: {len(text)}자")

                    # 필드 찾기 시도
                    try:
                        field_text = doc.get_field_text("test")
                        print(f"✓ 필드 검색 테스트 완료")
                    except:
                        print("ℹ 필드 기능 테스트 (필드가 없는 파일)")

                    # 표 찾기
                    tables = doc.get_tables()
                    print(f"✓ 표 발견: {len(tables)}개")

                    # 주석 찾기
                    comments = doc.find_comments()
                    print(f"✓ 주석 발견: {len(comments)}개")

                    for i, comment in enumerate(comments):
                        comment_text = doc.get_comment_text(comment)
                        print(f"  주석 {i+1}: {comment_text[:50] if comment_text else '텍스트 없음'}...")

            except Exception as e:
                print(f"⚠ HWP 파일 처리 중 오류: {e}")

        # HWPX 기능 데모 (실제 파일이 있으면)
        hwpx_path = Path("tests/data/sample1.hwpx")
        if hwpx_path.exists():
            print(f"\n📖 HWPX 파일 읽기 예제 ({hwpx_path.name}):")
            try:
                with parser.read(hwpx_path) as doc:
                    text = doc.extract_text()
                    print(f"✓ 텍스트 추출 성공: {len(text)}자")

                    # 객체 찾기
                    tables = doc.find_tables()
                    images = doc.find_images()
                    paragraphs = doc.find_paragraphs()
                    print(f"✓ 표 발견: {len(tables)}개")
                    print(f"✓ 이미지 발견: {len(images)}개")
                    print(f"✓ 문단 발견: {len(paragraphs)}개")

                    # 메모 기능
                    memo_props = doc.find_memo_properties()
                    print(f"✓ 메모 속성 발견: {len(memo_props)}개")

                    for i, memo in enumerate(memo_props):
                        info = doc.get_memo_info(memo)
                        print(f"  메모 {i+1}: ID={info.get('id')}, 너비={info.get('width')}")

            except Exception as e:
                print(f"⚠ HWPX 파일 처리 중 오류: {e}")

        print("\n🎉 라이브러리 구조 및 기본 기능 테스트 완료!")
        print("\n💡 다음 단계:")
        print("1. pip install JPype1")
        print("2. Java 7+ JDK/JRE 설치")
        print("3. 실제 HWP/HWPX 파일로 테스트")
        print("4. 고급 기능들 사용해보기")

        print("\n📚 지원되는 주요 기능들:")
        print("• 파일 읽기/쓰기")
        print("• 텍스트 추출")
        print("• 필드 조작 (HWP)")
        print("• 표 조작 (병합, 삭제)")
        print("• 컨트롤 찾기")
        print("• 이미지/하이퍼링크 삽입")
        print("• 객체 찾기 (HWPX)")

    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        print("라이브러리 설치 상태를 확인해주세요.")
        return 1
    except Exception as e:
        print(f"❌ 예기치 않은 오류: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
