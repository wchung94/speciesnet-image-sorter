"""Unit tests for thumbnail_creator module."""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap
from app.thumbnail_creator import create_thumbnail


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestThumbnailCreator:
    """Tests for thumbnail creation functionality."""

    def test_create_thumbnail_returns_pixmap(self, qapp, tmp_path):
        """Test that create_thumbnail returns a QPixmap."""
        # Create a minimal test image
        image_path = tmp_path / "test.png"

        # Create a simple QPixmap and save it
        original = QPixmap(100, 100)
        original.fill()
        original.save(str(image_path))

        result = create_thumbnail(str(image_path))

        assert isinstance(result, QPixmap)

    def test_create_thumbnail_scales_down(self, qapp, tmp_path):
        """Test that thumbnail is scaled to 64x64 or smaller."""
        # Create a large test image
        image_path = tmp_path / "large.png"

        original = QPixmap(200, 200)
        original.fill()
        original.save(str(image_path))

        thumbnail = create_thumbnail(str(image_path))

        # Should be scaled down, max dimension 64
        assert thumbnail.width() <= 64
        assert thumbnail.height() <= 64

    def test_create_thumbnail_maintains_aspect_ratio(self, qapp, tmp_path):
        """Test that thumbnail maintains aspect ratio."""
        # Create a rectangular test image
        image_path = tmp_path / "rect.png"

        original = QPixmap(200, 100)  # 2:1 aspect ratio
        original.fill()
        original.save(str(image_path))

        thumbnail = create_thumbnail(str(image_path))

        # Should maintain roughly 2:1 aspect ratio
        aspect_ratio = thumbnail.width() / thumbnail.height()
        assert 1.9 < aspect_ratio < 2.1

    def test_create_thumbnail_small_image(self, qapp, tmp_path):
        """Test thumbnail creation with already small image."""
        # Create a small test image
        image_path = tmp_path / "small.png"

        original = QPixmap(30, 30)
        original.fill()
        original.save(str(image_path))

        thumbnail = create_thumbnail(str(image_path))

        # Should still work, might be scaled up or kept same
        assert isinstance(thumbnail, QPixmap)
        assert not thumbnail.isNull()
