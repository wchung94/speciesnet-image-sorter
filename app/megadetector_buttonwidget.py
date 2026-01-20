from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QPushButton, QHBoxLayout, QMessageBox
import os
import logging
from .speciesnet_buttonwidget import SpeciesnetWorker

class MegaDetectorWidget(QWidget):
    """Widget that places a 'Run Megadetector' button at the left-bottom corner.
    When clicked it checks for predictions.json in the current folder and runs
    megadetector's visualization command in a worker thread.
    """
    def __init__(self, name):
        super().__init__()
        self.folder_path = ""
        self.folder_name = name
        self.worker = None
        self.logger = logging.getLogger("ImageViewer")
        
        vlayout = QVBoxLayout()
        vlayout.addStretch()  # push buttons to the bottom row

        hbox = QHBoxLayout()
        self.run_button = QPushButton("MegaDetector")
        self.run_button.clicked.connect(self.on_run_clicked)

        hbox.addWidget(self.run_button)  # left side
        hbox.addStretch()  # push button to left

        vlayout.addLayout(hbox)
        self.setLayout(vlayout)
    
    def on_run_clicked(self):
        window = self.window()
        folder = None
        if window and hasattr(window, "current_folder") and window.current_folder:
            folder = window.current_folder

        if not folder:
            folder = QFileDialog.getExistingDirectory(self, "Select folder to run MegaDetector on")
            if not folder:
                return

        predictions_json = os.path.join(folder, "predictions.json")
        if not os.path.isfile(predictions_json):
            msg = f"No predictions.json found in folder:\n{folder}"
            QMessageBox.warning(self, "MegaDetector", msg)
            self.logger.warning(msg)
            return

        # prepare output folder for visualization
        output_dir = os.path.join(folder, "megadetector_output")
        output_dir = folder
        # store output_dir so renaming runs on the same directory used by the command
        self.output_dir = output_dir
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "MegaDetector", f"Failed to create output directory:\n{e}")
            self.logger.error(f"Failed to create output directory {output_dir}: {e}")
            return

        # command to run megadetector visualization
        cmd = [
            "python", "-m",
            "megadetector.visualization.visualize_detector_output",
            predictions_json,
            output_dir
        ]

        try:
            # reuse SpeciesnetWorker that captures stdout/stderr and emits signals
            self.worker = SpeciesnetWorker(cmd, folder)
            self.worker.output_signal.connect(self.on_output)
            self.worker.error_signal.connect(self.on_error)
            self.worker.finished_signal.connect(self.on_finished)
            self.worker.start()

            self.run_button.setEnabled(False)
            self.logger.info(f"MegaDetector process started for: {folder}")
        except Exception as e:
            error_msg = f"Failed to start MegaDetector: {str(e)}"
            QMessageBox.critical(self, "MegaDetector Error", error_msg)
            self.logger.error(error_msg)
    
    def on_output(self, message):
        """Handle output lines from the worker."""
        self.logger.info(message)
    
    def on_error(self, message):
        """Handle error output from the worker."""
        self.logger.error(message)
    
    def on_finished(self):
        """Re-enable button when finished and rename output files."""
        self.run_button.setEnabled(True)
        self.logger.info("MegaDetector process finished")

        # Attempt to rename output files produced by MegaDetector
        try:
          # prefer the explicit output_dir used when starting MegaDetector
            output_dir = getattr(self, "output_dir", None)
            # fallback: if output_dir not set, try worker.folder or widget.folder_path
            if not output_dir:
                if self.worker and hasattr(self.worker, "folder"):
                    output_dir = os.path.join(self.worker.folder, "megadetector_output")
                elif self.folder_path:
                    output_dir = os.path.join(self.folder_path, "megadetector_output") 
            if output_dir:
                self.rename_output_files(output_dir)
                self.logger.info("Renamed MegaDetector output files (if any).")
            else:
                self.logger.debug("No folder available to rename MegaDetector output files.")
        except Exception as e:
            self.logger.error(f"Error renaming MegaDetector output files: {e}")

    def rename_output_files(self, folder):
        """Rename files in megadetector_output so only the part after the last '~' remains,
        and add a '_pred' postfix before the extension. If a target name already exists,
        append a numeric suffix to avoid overwriting.
        """
        output_dir = folder
        if not os.path.isdir(output_dir):
            self.logger.warning(f"rename_output_files: output directory not found: {output_dir}")
            return
        
        for fname in os.listdir(output_dir):
            src_path = os.path.join(output_dir, fname)
            if not os.path.isfile(src_path):
                continue

            if "~" not in fname:
                continue

            raw_name = fname.split("~")[-1].strip()
            if not raw_name:
                self.logger.debug(f"Skipping rename for {fname}: empty target name after '~'")
                continue

            base, ext = os.path.splitext(raw_name)
            # add '_pred' postfix to the base name
            base_pred = f"{base}_pred"
            dst_name = f"{base_pred}{ext}"
            dst_path = os.path.join(output_dir, dst_name)

            # avoid overwriting existing files by adding numeric suffix
            counter = 1
            while os.path.exists(dst_path):
                dst_name = f"{base_pred}_{counter}{ext}"
                dst_path = os.path.join(output_dir, dst_name)
                counter += 1

            try:
                os.rename(src_path, dst_path)
                self.logger.info(f"Renamed '{fname}' -> '{os.path.basename(dst_path)}'")
            except Exception as e:
                self.logger.error(f"Failed to rename '{src_path}' -> '{dst_path}': {e}")
