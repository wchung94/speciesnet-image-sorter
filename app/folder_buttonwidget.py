from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QTabWidget
import os


class FolderTab(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setTabPosition(QTabWidget.TabPosition.South)
        self.setMovable(True)

        # Initialize tabs with empty folders
        self.addTab(FolderWidget("Folder 1"), "[1] Select Folder")
        self.addTab(FolderWidget("Folder 2"), "[2] Select Folder")
        self.addTab(FolderWidget("Folder 2"), "[3] Select Folder")

        # Connect tab clicked event
        self.tabBarClicked.connect(self.handle_tab_click)

    def handle_tab_click(self, index):
        """Handle tab click by opening folder dialog"""
        current_widget = self.widget(index)
        folder_path = QFileDialog.getExistingDirectory(
            self, f"Select folder for Tab {index + 1}"
        )
        if folder_path:
            current_widget.set_folder_path(folder_path)
            # Include the key number in the tab text
            self.setTabText(index, f"[{index + 1}] {os.path.basename(folder_path)}")


class FolderWidget(QWidget):
    def __init__(self, name):
        super().__init__()
        self.folder_path = ""
        self.folder_name = name

        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)

    def set_folder_path(self, path):
        """Set the folder path for this widget"""
        self.folder_path = path

    def get_folder_path(self):
        """Get the current folder path"""
        return self.folder_path
