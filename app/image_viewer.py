from PyQt6.QtWidgets import (QLabel, QMainWindow, QFileDialog, QListWidget, 
                             QListWidgetItem, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QPushButton, QTabWidget, QTextEdit)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize
import logging
from .folder_buttonwidget import FolderTab
from .image_loader import load_image, load_folder_images
from .thumbnail_creator import create_thumbnail
from .file_operations import copy_current_image_to_new_folder
from .speciesnet_buttonwidget import SpeciesnetWidget
from .megadetector_buttonwidget import MegaDetectorWidget
from .logs_window import LogHandler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize variables
        self.current_folder = None
        self.image_files = []
        self.current_image_index = -1
        self.new_folder_path = ["folder_1", "folder_2"]

        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar().show()
        
        # Create image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create file list widget
        self.file_list = QListWidget()
        self.file_list.setIconSize(QSize(64, 64))
        self.file_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.file_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.file_list.setWrapping(True)
        self.file_list.setSpacing(10)
        self.file_list.itemClicked.connect(self.on_file_selected)
        self.file_list.setMovement(QListWidget.Movement.Static)
        self.file_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Create terminal log window
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        # Prevent log window from accepting keyboard focus
        self.log_text.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Setup logging
        self.logger = logging.getLogger("ImageViewer")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create custom handler for QTextEdit
        log_handler = LogHandler(self.log_text)
        log_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(log_handler)
        
        # Log startup message
        self.logger.info("=== Application Started ===")
        self.logger.info("Logger initialized successfully")

        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create horizontal splitter for file list and image
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.addWidget(self.file_list)
        content_splitter.addWidget(self.image_label)
        content_splitter.setStretchFactor(1, 1)

        # Create folder tabs
        self.tabs = FolderTab()
        self.speciesnet_widget = SpeciesnetWidget("SpeciesNet")
        self.speciesnet_widget.setMaximumWidth(220)

        # create Megadetector button and stack it under SpeciesNet
        self.megadetector_button = MegaDetectorWidget("Megadetector")
        self.megadetector_button.setMaximumWidth(220)

        # left column stacks SpeciesNet and Megadetector horizontally
        left_stack = QWidget()
        left_layout = QHBoxLayout()
        left_layout.setContentsMargins(1, 1, 1, 1)   # small margins
        left_layout.setSpacing(4)
        left_layout.addWidget(self.speciesnet_widget)
        left_layout.addWidget(self.megadetector_button)
        left_layout.addStretch(1)
        left_stack.setLayout(left_layout)
        # ensure the left_stack is aligned to the very left of the bottom area
        left_layout.addStretch(1)
        
        # Bottom area: speciesnet button at left, folder tabs to the right
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(left_stack)
        bottom_layout.addWidget(self.tabs, 1)
        bottom_container.setLayout(bottom_layout)

        # Add widgets to main splitter
        main_splitter.addWidget(content_splitter)
        main_splitter.addWidget(bottom_container)
        main_splitter.addWidget(self.log_text)
        main_splitter.setStretchFactor(0, 5)
        main_splitter.setStretchFactor(1, 0)
        main_splitter.setStretchFactor(2, 1)
        
        self.setCentralWidget(main_splitter)
        
        # Set focus to the main window to ensure key presses are captured
        self.setFocus()

    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        # Add Open File action
        open_file_action = file_menu.addAction("Open File")
        open_file_action.triggered.connect(self.open_image)
        
        # Add Open Folder action
        open_folder_action = file_menu.addAction("Open Folder")
        open_folder_action.triggered.connect(self.open_folder)

    def open_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_name:
            self.logger.info(f"Opened image: {file_name}")
            load_image(file_name, self.image_label)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Open Folder",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            self.current_folder = folder_path
            self.logger.info(f"Opened folder: {folder_path}")
            self.load_folder_images()

    def load_folder_images(self):
        """Load all image files from the current folder."""
        if not self.current_folder:
            return
            
        self.image_files = load_folder_images(self.current_folder, self.file_list)
        self.logger.info(f"Loaded {len(self.image_files)} images")
        
        if self.image_files:
            self.current_image_index = 0
            load_image(self.image_files[0], self.image_label)
            self.file_list.setCurrentRow(0)
        else:
            self.current_image_index = -1
            self.image_label.clear()
            self.image_label.setText("No images found in the selected folder")
            self.logger.warning("No images found in the selected folder")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_Down:
            self.next_image()
        elif event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_Up:
            self.previous_image()
        elif event.key() == Qt.Key.Key_1:
            tab = self.tabs.widget(0)
            if tab and tab.get_folder_path():
                self.logger.info(f"Copying to folder 1: {tab.get_folder_path()}")
                copy_current_image_to_new_folder(
                    tab.get_folder_path(), 
                    self.image_files, 
                    self.current_image_index
                )
        elif event.key() == Qt.Key.Key_2:
            tab = self.tabs.widget(1)
            if tab and tab.get_folder_path():
                self.logger.info(f"Copying to folder 2: {tab.get_folder_path()}")
                copy_current_image_to_new_folder(
                    tab.get_folder_path(), 
                    self.image_files, 
                    self.current_image_index
                )
        elif event.key() == Qt.Key.Key_3:
            tab = self.tabs.widget(2)
            if tab and tab.get_folder_path():
                self.logger.info(f"Copying to folder 3: {tab.get_folder_path()}")
                copy_current_image_to_new_folder(
                    tab.get_folder_path(), 
                    self.image_files, 
                    self.current_image_index
                )
        else:
            super().keyPressEvent(event)

    def on_file_selected(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        self.current_image_index = self.image_files.index(file_path)
        self.logger.debug(f"Selected image: {file_path}")
        load_image(file_path, self.image_label)

    def next_image(self):
        if not self.image_files or self.current_image_index == -1:
            return
            
        self.current_image_index = (self.current_image_index + 1) % len(self.image_files)
        self.logger.debug(f"Next image: {self.image_files[self.current_image_index]}")
        load_image(self.image_files[self.current_image_index], self.image_label)
        self.file_list.setCurrentRow(self.current_image_index)

    def previous_image(self):
        if not self.image_files or self.current_image_index == -1:
            return
            
        self.current_image_index = (self.current_image_index - 1) % len(self.image_files)
        self.logger.debug(f"Previous image: {self.image_files[self.current_image_index]}")
        load_image(self.image_files[self.current_image_index], self.image_label)
        self.file_list.setCurrentRow(self.current_image_index)