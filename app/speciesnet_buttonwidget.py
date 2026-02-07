from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QTabWidget, QPushButton, QHBoxLayout, QMessageBox
import os
import logging
from glob import glob
from .worker import SpeciesnetWorker


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

        try:
            cmd = [
                "python", "-m", "speciesnet.scripts.run_model",
                #"--folders", folder,
                "--filepaths", image_files,
                "--predictions_json", predictions_json,
                "country", "NL"
            ]
            
            # Create and start worker thread
            self.worker = SpeciesnetWorker(cmd, folder)
            self.worker.output_signal.connect(self.on_output)
            self.worker.error_signal.connect(self.on_error)
            self.worker.finished_signal.connect(self.on_finished)
            # Properly cleanup the thread when done to prevent segfaults
            self.worker.finished.connect(self.worker.deleteLater)
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
        self.run_button.setEnabled(True)
        self.logger.info("SpeciesNet process finished")