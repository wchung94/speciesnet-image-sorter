from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFileDialog,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt
import os
import sys
import logging
from glob import glob
from .worker import SpeciesnetWorker
from .video_utils import get_video_files, extract_frames


class SpeciesnetWidget(QWidget):
    """Widget that places a 'Run SpeciesNet' button at the left-bottom corner.
    When clicked it runs SpeciesNet on the currently opened folder (from MainWindow.current_folder)
    or asks the user to choose a folder if none is open.
    Supports both image and video files - extracts frames from videos before processing.
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

    def extract_video_frames(self, folder):
        """
        Extract frames from all videos in the folder.

        Args:
            folder: Path to the folder containing videos

        Returns:
            List of folders containing extracted frames
        """
        video_files = get_video_files(folder)
        if not video_files:
            self.logger.info("No video files found in folder")
            return []

        self.logger.info(f"Found {len(video_files)} video file(s) to process")
        extracted_frame_folders = []

        for video_file in video_files:
            self.logger.info(f"Extracting frames from: {os.path.basename(video_file)}")
            result = extract_frames(video_file, frame_interval=30)

            if result["success"]:
                self.logger.info(f"✓ {result['message']}")
                extracted_frame_folders.append(result["output_folder"])
            else:
                self.logger.warning(f"✗ {result['message']}")

        return extracted_frame_folders

    def on_run_clicked(self):
        # Try to use MainWindow.current_folder if available
        window = self.window()
        folder = None
        if window and hasattr(window, "current_folder") and window.current_folder:
            folder = window.current_folder

        if not folder:
            folder = QFileDialog.getExistingDirectory(
                self, "Select folder to run SpeciesNet on"
            )
            if not folder:
                return

        # Check for videos and extract frames
        extracted_frame_folders = self.extract_video_frames(folder)

        # Collect all image files (both original and extracted from videos)
        image_files = list(glob(os.path.join(folder, "*.JPG")))
        image_files.extend(glob(os.path.join(folder, "*.jpg")))

        # Add extracted frames from videos
        for frame_folder in extracted_frame_folders:
            image_files.extend(glob(os.path.join(frame_folder, "*.jpg")))

        # Remove duplicates while preserving order
        image_files = list(dict.fromkeys(image_files))

        if not image_files:
            QMessageBox.warning(
                self,
                "SpeciesNet",
                f"No image files found in:\n{folder}\n\nMake sure videos are processed or images exist.",
            )
            self.logger.warning("No image files or videos found in folder")
            return

        predictions_json = os.path.join(folder, "predictions.json")
        filepaths_txt = os.path.join(folder, "speciesnet_filepaths.txt")

        # Stop any existing worker first
        if self.worker and self.worker.isRunning():
            self.logger.warning("Stopping previous SpeciesNet worker...")
            self.worker.terminate_process()
            self.worker.quit()
            self.worker.wait(2000)
            self.worker = None

        try:
            # Writing file paths to a text file avoids Windows command-line length limits.
            with open(filepaths_txt, "w", encoding="utf-8") as f:
                f.write("\n".join(image_files))

            cmd = [
                sys.executable,
                "-m",
                "speciesnet.scripts.run_model",
                "--filepaths_txt",
                filepaths_txt,
                "--predictions_json",
                predictions_json,
                "--country",
                "NLD",
            ]

            # Create and start worker thread
            self.worker = SpeciesnetWorker(cmd, folder)
            # Set parent to ensure proper cleanup
            self.worker.setParent(self)
            self.worker.output_signal.connect(
                self.on_output, Qt.ConnectionType.QueuedConnection
            )
            self.worker.error_signal.connect(
                self.on_error, Qt.ConnectionType.QueuedConnection
            )
            self.worker.finished_signal.connect(
                self.on_finished, Qt.ConnectionType.QueuedConnection
            )
            # Don't delete the worker - keep it alive to prevent segfaults
            # Qt will clean it up when the parent widget is destroyed
            self.worker.start()

            self.run_button.setEnabled(False)
            total_files = len(image_files)
            self.logger.info(f"SpeciesNet process started for: {folder}")
            self.logger.info(
                f"Processing {total_files} images (including video frames)"
            )

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
            if window and hasattr(window, "load_folder_images") and self.worker:
                folder = self.worker.folder
                if folder:
                    window.current_folder = folder
                    window.load_folder_images()
                    self.logger.info(f"Loaded images from processed folder: {folder}")
        except RuntimeError as e:
            # Widget was deleted
            self.logger.debug(f"Widget deleted during on_finished: {e}")
