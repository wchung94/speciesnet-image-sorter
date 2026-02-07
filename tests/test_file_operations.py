"""Unit tests for file_operations module."""
import os
import tempfile
import shutil
import pytest
from app.file_operations import copy_current_image_to_new_folder


class TestFileOperations:
    """Tests for file operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, "source")
        self.dest_dir = os.path.join(self.test_dir, "dest")
        os.makedirs(self.source_dir)
        os.makedirs(self.dest_dir)
        
        # Create test image files
        self.image_files = []
        for i in range(3):
            image_path = os.path.join(self.source_dir, f"image_{i}.jpg")
            with open(image_path, 'w') as f:
                f.write(f"fake image {i}")
            self.image_files.append(image_path)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_copy_current_image_to_new_folder(self):
        """Test copying current image to new folder."""
        current_index = 1
        copy_current_image_to_new_folder(
            self.dest_dir, 
            self.image_files, 
            current_index
        )
        
        # Verify file was copied
        expected_file = os.path.join(self.dest_dir, "image_1.jpg")
        assert os.path.exists(expected_file)
        
        # Verify content
        with open(expected_file, 'r') as f:
            content = f.read()
        assert content == "fake image 1"
    
    def test_copy_with_empty_folder_path(self):
        """Test that copy doesn't fail with empty folder path."""
        # Should not raise an exception
        copy_current_image_to_new_folder("", self.image_files, 0)
        
        # Verify nothing was copied to dest_dir
        files_in_dest = os.listdir(self.dest_dir)
        assert len(files_in_dest) == 0
    
    def test_copy_with_empty_image_files(self):
        """Test that copy doesn't fail with empty image files list."""
        # Should not raise an exception
        copy_current_image_to_new_folder(self.dest_dir, [], 0)
        
        # Verify nothing was copied
        files_in_dest = os.listdir(self.dest_dir)
        assert len(files_in_dest) == 0
    
    def test_copy_first_image(self):
        """Test copying the first image in the list."""
        copy_current_image_to_new_folder(self.dest_dir, self.image_files, 0)
        
        expected_file = os.path.join(self.dest_dir, "image_0.jpg")
        assert os.path.exists(expected_file)
    
    def test_copy_last_image(self):
        """Test copying the last image in the list."""
        copy_current_image_to_new_folder(self.dest_dir, self.image_files, 2)
        
        expected_file = os.path.join(self.dest_dir, "image_2.jpg")
        assert os.path.exists(expected_file)
