from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QTabWidget, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal
import os
import subprocess
import logging
from glob import glob

class SpeciesnetWorker(QThread):
    """Worker thread to run SpeciesNet without blocking the UI."""
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, cmd, folder):
        super().__init__()
        self.cmd = cmd
        self.folder = folder
        self.logger = logging.getLogger("ImageViewer")
    
    def run(self):
        try:
            self.output_signal.emit(f"Starting SpeciesNet on folder: {self.folder}")
            self.logger.info(f"Starting SpeciesNet on folder: {self.folder}")
            
            # Run subprocess with output capture
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Read stdout and stderr in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.output_signal.emit(output.strip())
                    self.logger.info(output.strip())
            
            # Get any remaining stderr
            _, stderr = process.communicate()
            if stderr:
                self.error_signal.emit(stderr)
                self.logger.error(stderr)
            
            return_code = process.returncode
            if return_code == 0:
                self.output_signal.emit("SpeciesNet completed successfully")
                self.logger.info("SpeciesNet completed successfully")
            else:
                self.error_signal.emit(f"SpeciesNet exited with code {return_code}")
                self.logger.error(f"SpeciesNet exited with code {return_code}")
            
            self.finished_signal.emit()
            
        except Exception as e:
            error_msg = f"Failed to run SpeciesNet: {str(e)}"
            self.error_signal.emit(error_msg)
            self.logger.error(error_msg)
            self.finished_signal.emit()


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