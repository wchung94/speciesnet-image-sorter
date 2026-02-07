from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QTabWidget, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
import os
import sys
import logging
from glob import glob
from .worker import SpeciesnetWorker
import time

class SpeciesnetWidget(QWidget):
    """Widget that places a 'Run SpeciesNet' button at the left-bottom corner.
    When clicked it runs SpeciesNet on the currently opened folder (from MainWindow.current_folder)
    or asks the user to choose a folder if none is open.
    """
    def __init__(self, name):
        super().__init__()
        self.folder_path = ""
        self.folder_name = name
        self.worker = None
        self.logger = logging.getLogger("ImageViewer")
        
        # Main vertical layout: stretch, then a horizontal layout containing button on the left
        vlayout = QVBoxLayout()
        vlayout.addStretch()  # push button row to the bottom

        hbox = QHBoxLayout()
        self.run_button = QPushButton("SpeciesNet")
        self.run_button.clicked.connect(self.on_run_clicked)

        hbox.addWidget(self.run_button)  # left side
        hbox.addStretch()  # push button to left

        vlayout.addLayout(hbox)
        self.setLayout(vlayout)
    
    def on_run_clicked(self):
        # Try to use MainWindow.current_folder if available
        window = self.window()
        folder = None
        if window and hasattr(window, "current_folder") and window.current_folder:
            folder = window.current_folder

        if not folder:
            folder = QFileDialog.getExistingDirectory(self, "Select folder to run SpeciesNet on")
            if not folder:
                return

        predictions_json = os.path.join(folder, "predictions.json")

        image_files = ",".join(glob(os.path.join(folder, "*.JPG")))

        # Stop any existing worker first
        if self.worker and self.worker.isRunning():
            self.logger.warning("Stopping previous SpeciesNet worker...")
            self.worker.terminate_process()
            self.worker.quit()
            self.worker.wait(2000)
            self.worker = None

        try:
            cmd = [
                sys.executable, "-m", "speciesnet.scripts.run_model",
                #"--folders", folder,
                "--filepaths", image_files,
                "--predictions_json", predictions_json,
                "country", "NL"
            ]
            
            # Create and start worker thread
            self.worker = SpeciesnetWorker(cmd, folder)
            # Set parent to ensure proper cleanup
            self.worker.setParent(self)
            self.worker.output_signal.connect(self.on_output, Qt.ConnectionType.QueuedConnection)
            self.worker.error_signal.connect(self.on_error, Qt.ConnectionType.QueuedConnection)
            self.worker.finished_signal.connect(self.on_finished, Qt.ConnectionType.QueuedConnection)
            # Don't delete the worker - keep it alive to prevent segfaults
            # Qt will clean it up when the parent widget is destroyed
            self.worker.start()
            
            self.run_button.setEnabled(False)
            self.logger.info(f"SpeciesNet process started for: {folder}")
            
        except Exception as e:
            error_msg = f"Failed to start SpeciesNet: {str(e)}"
            QMessageBox.critical(self, "SpeciesNet Error", error_msg)
            self.logger.error(error_msg)
    
    def on_output(self, message):
        """Handle output from SpeciesNet process."""
        pass  # Already logged in the worker thread
    
    def on_error(self, message):
        """Handle errors from SpeciesNet process."""
        pass  # Already logged in the worker thread
    
    def on_finished(self):
        """Handle completion of SpeciesNet process."""
        try:
            if self.run_button and not self.run_button.isHidden():
                self.run_button.setEnabled(True)
            self.logger.info("SpeciesNet process finished")
            
            # Load images from the processed folder
            window = self.window()
            if window and hasattr(window, 'load_folder_images') and self.worker:
                folder = self.worker.folder
                if folder:
                    window.current_folder = folder
                    window.load_folder_images()
                    self.logger.info(f"Loaded images from processed folder: {folder}")
        except RuntimeError as e:
            # Widget was deleted
            self.logger.debug(f"Widget deleted during on_finished: {e}")
