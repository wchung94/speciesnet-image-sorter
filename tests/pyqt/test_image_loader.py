"""Unit tests for image_loader module."""

import os
import tempfile
import shutil
import pytest
from PyQt6.QtWidgets import QApplication, QListWidget
from app.image_loader import load_folder_images


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestImageLoader:
    """Tests for image loading functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()

        # Create test image files (empty files with image extensions)
        self.image_files = []
        for ext in ["jpg", "png", "jpeg", "bmp"]:
            image_path = os.path.join(self.test_dir, f"test_image.{ext}")
            # Create a minimal valid image file (1x1 pixel)
            with open(image_path, "wb") as f:
                if ext in ["jpg", "jpeg"]:
                    # Minimal JPEG header
                    f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")
                elif ext == "png":
                    # Minimal PNG header
                    f.write(b"\x89PNG\r\n\x1a\n")
                else:
                    # For other formats, write something
                    f.write(b"BM")
            self.image_files.append(image_path)

        # Create non-image files (should be ignored)
        text_file = os.path.join(self.test_dir, "readme.txt")
        with open(text_file, "w") as f:
            f.write("not an image")

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_load_folder_images(self, qapp):
        """Test loading images from a folder."""
        file_list = QListWidget()

        images = load_folder_images(self.test_dir, file_list)

        # Should find 4 image files
        assert len(images) == 4

        # Should have 4 items in the list widget
        assert file_list.count() == 4

        # All returned paths should be image files
        for img_path in images:
            assert os.path.splitext(img_path)[1].lower() in [
                ".jpg",
                ".png",
                ".jpeg",
                ".bmp",
            ]

    def test_load_folder_images_sorted(self, qapp):
        """Test that images are loaded in sorted order."""
        file_list = QListWidget()

        images = load_folder_images(self.test_dir, file_list)

        # Create sorted list of expected files
        expected = sorted([os.path.basename(f) for f in self.image_files])

        # Verify images are in sorted order
        actual = [os.path.basename(img) for img in images]
        assert actual == expected

    def test_load_folder_images_clears_list(self, qapp):
        """Test that loading images clears the previous list."""
        file_list = QListWidget()

        # Add some initial items
        file_list.addItem("Item 1")
        file_list.addItem("Item 2")
        assert file_list.count() == 2

        # Load images
        load_folder_images(self.test_dir, file_list)

        # Should have replaced items, not appended
        assert file_list.count() == 4

    def test_load_folder_images_empty_folder(self, qapp):
        """Test loading images from an empty folder."""
        empty_dir = os.path.join(self.test_dir, "empty")
        os.makedirs(empty_dir)

        file_list = QListWidget()
        images = load_folder_images(empty_dir, file_list)

        assert len(images) == 0
        assert file_list.count() == 0
