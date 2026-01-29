"""
Tests for image extraction functionality.

TDD approach: RED -> GREEN -> REFACTOR
"""

import pytest
from pathlib import Path
from hwp_hwpx_parser.models import ImageData, detect_image_format
from hwp_hwpx_parser import HWP5Reader, HWPXReader, Reader
import tempfile


TESTS_DATA_DIR = Path(__file__).parent / "data"

# Test file availability flags
HAS_HWP5_IMAGES = (TESTS_DATA_DIR / "글상자.hwp").exists()
HAS_HWPX_IMAGES = (TESTS_DATA_DIR / "sample1.hwpx").exists()


class TestImageData:
    """Test ImageData dataclass."""

    def test_image_data_creation(self):
        """Test creating ImageData instance."""
        data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        img = ImageData(filename="test.png", data=data, index=0, format="png")
        assert img.filename == "test.png"
        assert img.data == data
        assert img.index == 0
        assert img.format == "png"
        assert img.width is None
        assert img.height is None

    def test_image_data_with_dimensions(self):
        """Test ImageData with width and height."""
        data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        img = ImageData(
            filename="test.png", data=data, index=0, format="png", width=100, height=200
        )
        assert img.width == 100
        assert img.height == 200

    def test_image_data_optional_filename(self):
        """Test ImageData with None filename."""
        data = b"\xff\xd8\xff" + b"fake_jpg_data"
        img = ImageData(filename=None, data=data, index=1, format="jpg")
        assert img.filename is None
        assert img.format == "jpg"

    def test_image_data_save_creates_file(self, tmp_path):
        """Test ImageData.save() creates file."""
        data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        img = ImageData(filename="test.png", data=data, index=0, format="png")

        output_file = tmp_path / "test.png"
        img.save(output_file)

        assert output_file.exists()
        assert output_file.read_bytes() == data

    def test_image_data_save_with_string_path(self, tmp_path):
        """Test ImageData.save() with string path."""
        data = b"\xff\xd8\xff" + b"fake_jpg_data"
        img = ImageData(filename="test.jpg", data=data, index=0, format="jpg")

        output_file = str(tmp_path / "test.jpg")
        img.save(output_file)

        assert Path(output_file).exists()
        assert Path(output_file).read_bytes() == data


class TestDetectImageFormat:
    """Test detect_image_format function."""

    def test_detect_png(self):
        """Test PNG detection."""
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        assert detect_image_format(png_data) == "png"

    def test_detect_jpg(self):
        """Test JPG detection."""
        jpg_data = b"\xff\xd8\xff" + b"fake_jpg_data"
        assert detect_image_format(jpg_data) == "jpg"

    def test_detect_gif87a(self):
        """Test GIF87a detection."""
        gif_data = b"GIF87a" + b"fake_gif_data"
        assert detect_image_format(gif_data) == "gif"

    def test_detect_gif89a(self):
        """Test GIF89a detection."""
        gif_data = b"GIF89a" + b"fake_gif_data"
        assert detect_image_format(gif_data) == "gif"

    def test_detect_bmp(self):
        """Test BMP detection."""
        bmp_data = b"BM" + b"fake_bmp_data"
        assert detect_image_format(bmp_data) == "bmp"

    def test_detect_emf(self):
        """Test EMF detection."""
        emf_data = b"\x01\x00\x00\x00" + b"fake_emf_data"
        assert detect_image_format(emf_data) == "emf"

    def test_detect_wmf(self):
        """Test WMF detection."""
        wmf_data = b"\xd7\xcd\xc6\x9a" + b"fake_wmf_data"
        assert detect_image_format(wmf_data) == "wmf"

    def test_detect_unknown(self):
        """Test unknown format detection."""
        unknown_data = b"UNKNOWN_FORMAT" + b"fake_data"
        assert detect_image_format(unknown_data) == "unknown"

    def test_detect_empty_data(self):
        """Test empty data detection."""
        assert detect_image_format(b"") == "unknown"

    def test_detect_short_data(self):
        """Test short data detection."""
        assert detect_image_format(b"X") == "unknown"


class TestHWP5Images:
    """Test HWP5 image extraction."""

    @pytest.fixture
    def hwp_file_with_images(self):
        return TESTS_DATA_DIR / "글상자.hwp"

    @pytest.fixture
    def sample_notes_file(self):
        return TESTS_DATA_DIR / "sample_notes.hwp"

    @pytest.mark.skipif(
        not HAS_HWP5_IMAGES, reason="No HWP5 test files with images available"
    )
    def test_hwp5_file_exists(self, hwp_file_with_images):
        """Test that HWP5 test file exists."""
        assert hwp_file_with_images.exists()

    @pytest.mark.skipif(
        not HAS_HWP5_IMAGES, reason="No HWP5 test files with images available"
    )
    def test_get_images_returns_list(self, hwp_file_with_images):
        """Test get_images() returns list of ImageData."""
        reader = HWP5Reader(hwp_file_with_images)
        images = reader.get_images()

        assert isinstance(images, list)
        assert len(images) > 0

        # Verify all items are ImageData instances
        for img in images:
            assert isinstance(img, ImageData)
            assert img.data is not None
            assert img.format != "unknown"
            assert img.index >= 0

    @pytest.mark.skipif(
        not HAS_HWP5_IMAGES, reason="No HWP5 test files with images available"
    )
    def test_image_has_correct_format(self, hwp_file_with_images):
        """Test extracted images have valid format and data."""
        reader = HWP5Reader(hwp_file_with_images)
        images = reader.get_images()

        valid_formats = ["png", "jpg", "gif", "bmp", "emf", "wmf"]

        for img in images:
            assert img.format in valid_formats
            assert len(img.data) > 0
            assert detect_image_format(img.data) == img.format

    @pytest.mark.skipif(
        not HAS_HWP5_IMAGES, reason="No HWP5 test files with images available"
    )
    def test_encrypted_file_raises_error(self, hwp_file_with_images):
        """Test encrypted files raise ValueError."""
        reader = HWP5Reader(hwp_file_with_images)

        if reader.is_encrypted():
            with pytest.raises(ValueError, match="Encrypted files are not supported"):
                reader.get_images()
        else:
            images = reader.get_images()
            assert isinstance(images, list)

    def test_test_v2_5_extracts_11_images(self):
        """Test that test-v2-5.hwp extracts 11 images."""
        filepath = Path(__file__).parent / "data" / "test" / "test-v2-5.hwp"
        if not filepath.exists():
            pytest.skip("test-v2-5.hwp not found")

        reader = HWP5Reader(str(filepath))
        images = reader.get_images()

        assert len(images) == 11, f"Expected 11 images, got {len(images)}"
        for img in images:
            assert img.format in ["png", "bmp", "jpg", "gif", "emf", "wmf"]
            assert len(img.data) > 0, "Image data should not be empty"


class TestHWPXImages:
    """Test HWPX image extraction."""

    @pytest.fixture
    def hwpx_file_with_images(self):
        return TESTS_DATA_DIR / "sample1.hwpx"

    @pytest.fixture
    def sample_notes_hwpx_file(self):
        return TESTS_DATA_DIR / "sample_notes.hwpx"

    @pytest.mark.skipif(
        not HAS_HWPX_IMAGES, reason="No HWPX test files with images available"
    )
    def test_hwpx_file_exists(self, hwpx_file_with_images):
        """Test that HWPX test file exists."""
        assert hwpx_file_with_images.exists()

    @pytest.mark.skipif(
        not HAS_HWPX_IMAGES, reason="No HWPX test files with images available"
    )
    def test_get_images_returns_list(self, hwpx_file_with_images):
        """Test get_images() returns list of ImageData."""
        reader = HWPXReader(hwpx_file_with_images)
        images = reader.get_images()

        assert isinstance(images, list)

        if len(images) > 0:
            for img in images:
                assert isinstance(img, ImageData)
                assert img.data is not None
                assert img.format != "unknown"
                assert img.index >= 0

    @pytest.mark.skipif(
        not HAS_HWPX_IMAGES, reason="No HWPX test files with images available"
    )
    def test_image_has_correct_format(self, hwpx_file_with_images):
        """Test extracted images have correct format."""
        reader = HWPXReader(hwpx_file_with_images)
        images = reader.get_images()

        if len(images) > 0:
            for img in images:
                assert img.format in ["png", "jpg", "gif", "bmp", "emf", "wmf"]
                assert detect_image_format(img.data) == img.format

    @pytest.mark.skipif(
        not HAS_HWPX_IMAGES, reason="No HWPX test files with images available"
    )
    def test_encrypted_file_raises_error(self, hwpx_file_with_images):
        """Test encrypted files raise error."""
        reader = HWPXReader(hwpx_file_with_images)

        if reader.is_encrypted():
            with pytest.raises(ValueError, match="Encrypted files are not supported"):
                reader.get_images()

    def test_test_v2_5_extracts_11_images(self):
        """Test that test-v2-5.hwpx extracts 11 images."""
        filepath = Path(__file__).parent / "data" / "test" / "test-v2-5.hwpx"
        if not filepath.exists():
            pytest.skip("test-v2-5.hwpx not found")

        reader = HWPXReader(str(filepath))
        images = reader.get_images()

        assert len(images) == 11, f"Expected 11 images, got {len(images)}"
        for img in images:
            assert img.format in ["png", "bmp", "jpg", "gif", "emf", "wmf"]
            assert len(img.data) > 0, "Image data should not be empty"


class TestReaderImages:
    """Test unified Reader image extraction."""

    @pytest.fixture
    def hwp_file_with_images(self):
        return TESTS_DATA_DIR / "글상자.hwp"

    @pytest.fixture
    def hwpx_file_with_images(self):
        return TESTS_DATA_DIR / "sample1.hwpx"

    @pytest.mark.skipif(
        not HAS_HWP5_IMAGES, reason="No HWP5 test files with images available"
    )
    def test_get_images_hwp5(self, hwp_file_with_images):
        """Test Reader.get_images() with HWP5 file."""
        with Reader(hwp_file_with_images) as reader:
            images = reader.get_images()

            assert isinstance(images, list)
            assert len(images) > 0
            for img in images:
                assert isinstance(img, ImageData)
                assert img.data is not None
                assert img.format != "unknown"

    @pytest.mark.skipif(
        not HAS_HWPX_IMAGES, reason="No HWPX test files with images available"
    )
    def test_get_images_hwpx(self, hwpx_file_with_images):
        """Test Reader.get_images() with HWPX file."""
        with Reader(hwpx_file_with_images) as reader:
            images = reader.get_images()

            assert isinstance(images, list)

    @pytest.mark.skipif(
        not HAS_HWP5_IMAGES, reason="No HWP5 test files with images available"
    )
    def test_save_images_creates_files(self, hwp_file_with_images):
        """Test Reader.save_images() creates files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with Reader(hwp_file_with_images) as reader:
                saved_paths = reader.save_images(tmpdir)

                assert isinstance(saved_paths, list)
                assert len(saved_paths) > 0
                for path in saved_paths:
                    assert Path(path).exists()
                    assert Path(path).stat().st_size > 0

    @pytest.mark.skipif(
        not HAS_HWP5_IMAGES, reason="No HWP5 test files with images available"
    )
    def test_save_images_creates_directory(self, hwp_file_with_images):
        """Test Reader.save_images() creates output directory if not exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "output"
            assert not output_dir.exists()

            with Reader(hwp_file_with_images) as reader:
                saved_paths = reader.save_images(output_dir)

                assert output_dir.exists()
                assert len(saved_paths) > 0
