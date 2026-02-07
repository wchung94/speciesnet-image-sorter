"""Unit tests for folder_buttonwidget module."""
import pytest
from PyQt6.QtWidgets import QApplication
from app.folder_buttonwidget import FolderTab, FolderWidget


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestFolderWidget:
    """Tests for FolderWidget class."""
    
    def test_init(self, qapp):
        """Test FolderWidget initialization."""
        widget = FolderWidget("Test Folder")
        
        assert widget.folder_name == "Test Folder"
        assert widget.folder_path == ""
    
    def test_set_folder_path(self, qapp):
        """Test setting folder path."""
        widget = FolderWidget("Test Folder")
        test_path = "/home/user/test"
        
        widget.set_folder_path(test_path)
        
        assert widget.get_folder_path() == test_path
    
    def test_get_folder_path_empty(self, qapp):
        """Test getting folder path when not set."""
        widget = FolderWidget("Test Folder")
        
        assert widget.get_folder_path() == ""


class TestFolderTab:
    """Tests for FolderTab class."""
    
    def test_init(self, qapp):
        """Test FolderTab initialization."""
        tab_widget = FolderTab()
        
        # Should have 3 tabs
        assert tab_widget.count() == 3
        
        # Check tab labels
        assert "[1] Select Folder" in tab_widget.tabText(0)
        assert "[2] Select Folder" in tab_widget.tabText(1)
        assert "[3] Select Folder" in tab_widget.tabText(2)
    
    def test_tabs_movable(self, qapp):
        """Test that tabs are movable."""
        tab_widget = FolderTab()
        
        assert tab_widget.isMovable() == True
    
    def test_widget_access(self, qapp):
        """Test accessing widgets in tabs."""
        tab_widget = FolderTab()
        
        # All widgets should be FolderWidget instances
        for i in range(tab_widget.count()):
            widget = tab_widget.widget(i)
            assert isinstance(widget, FolderWidget)
