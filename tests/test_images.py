"""
Tests for image extraction functionality.

TDD approach: RED -> GREEN -> REFACTOR
"""

import pytest
from pathlib import Path
from hwp_hwpx_parser.models import ImageData, detect_image_format


TESTS_DATA_DIR = Path(__file__).parent / "data"


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
