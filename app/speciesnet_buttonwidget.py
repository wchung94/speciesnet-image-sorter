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
import json
import logging
import re
from glob import glob
from .worker import SpeciesnetWorker
from .video_utils import get_video_files, extract_frames_batch


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
        Extract frames from all videos in the folder using the optimized batch processor.
        """
        video_files = get_video_files(folder)
        if not video_files:
            self.logger.info("No video files found in folder")
            return []

        self.logger.info(
            f"Found {len(video_files)} video file(s) to process in parallel"
        )
        extracted_frame_folders = []

        # Send all videos to our multi-core batch function!
        results = extract_frames_batch(video_files, frame_interval=30)

        # Log the results as they finish
        for result in results:
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

        # Remove duplicates while preserving order and force forward-slashes under Linux
        if sys.platform != "win32":
            image_files = [img.replace("\\", "/") for img in image_files]
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

        # Default run parameters
        target_image_files = image_files
        output_json = predictions_json
        self.is_resuming = False
        self.existing_data = None

        # --- STREAMLINED RAW TEXT PATH HARMONIZATION ---
        if os.path.exists(predictions_json):
            try:
                # Read the entire raw JSON payload as plain text
                with open(predictions_json, "r", encoding="utf-8") as f:
                    raw_content = f.read()

                # Clean up all mixed slash mutations to uniform forward-slashes
                raw_content = raw_content.replace("\\\\", "/").replace("\\", "/")

                # If running inside Linux/WSL, aggressively target and map all Windows-style references
                if sys.platform != "win32":
                    # Replace things like "C:/Users" with "/mnt/c/Users" case-insensitively
                    raw_content = re.sub(r'(?i)"C:/', '"/mnt/c/', raw_content)
                else:
                    # Conversely, if running on Windows, bring back the drive letter assignment
                    raw_content = re.sub(r'(?i)"/mnt/c/', '"C:/', raw_content)

                # Commit the cleaned plain text payload back to disk immediately
                with open(predictions_json, "w", encoding="utf-8") as f:
                    f.write(raw_content)

                # Now securely parse it back to a clean python dictionary object
                self.existing_data = json.loads(raw_content)

                processed_images = set()
                if (
                    isinstance(self.existing_data, dict)
                    and "images" in self.existing_data
                ):
                    for img in self.existing_data["images"]:
                        if "file" in img:
                            processed_images.add(os.path.normpath(img["file"]))

                normalized_target = [os.path.normpath(img) for img in image_files]

                # Extract only the items that haven't been accounted for yet
                unprocessed = [
                    img
                    for img, norm in zip(image_files, normalized_target)
                    if norm not in processed_images
                ]

                if len(unprocessed) == 0:
                    QMessageBox.information(
                        self,
                        "SpeciesNet",
                        f"All {len(image_files)} images are already processed in predictions.json.\n\nSkipping AI inference.",
                    )
                    self.logger.info(
                        "All images already present in predictions.json. Skipping."
                    )
                    return
                elif len(unprocessed) < len(image_files):
                    reply = QMessageBox.question(
                        self,
                        "Resume SpeciesNet",
                        f"Found {len(processed_images)} processed images and {len(unprocessed)} unprocessed images.\n\n"
                        "Do you want to RESUME and only process the remaining images?\n"
                        "(Choosing 'Yes' will safely merge the new results into your existing file without overwriting.)",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.is_resuming = True
                        target_image_files = unprocessed
                        output_json = os.path.join(folder, "predictions_temp.json")
                        self.logger.info(
                            f"Resuming: skipping {len(processed_images)} files, processing {len(unprocessed)} files."
                        )
                    else:
                        self.logger.info(
                            "User chose to overwrite existing predictions.json"
                        )
            except Exception as e:
                self.logger.warning(
                    f"Could not parse existing predictions.json for resuming: {e}"
                )
        # --------------------

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
                f.write("\n".join(target_image_files))

            cmd = [
                sys.executable,
                "-m",
                "speciesnet.scripts.run_model",
                "--filepaths_txt",
                filepaths_txt,
                "--predictions_json",
                output_json,
                "--country",
                "NLD",
            ]

            # Create and start worker thread
            self.worker = SpeciesnetWorker(cmd, folder)
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
            self.worker.start()

            self.run_button.setEnabled(False)
            total_files = len(target_image_files)
            self.logger.info(f"SpeciesNet process started for: {folder}")
            self.logger.info(f"Processing {total_files} images")

        except Exception as e:
            error_msg = f"Failed to start SpeciesNet: {str(e)}"
            QMessageBox.critical(self, "SpeciesNet Error", error_msg)
            self.logger.error(error_msg)

    def on_output(self, message):
        """Handle output from SpeciesNet process."""
        pass

    def on_error(self, message):
        """Handle errors from SpeciesNet process."""
        pass

    def on_finished(self):
        """Handle completion of SpeciesNet process."""
        try:
            folder = self.worker.folder if self.worker else None

            # --- MERGE LOGIC ---
            if getattr(self, "is_resuming", False) and folder:
                temp_json = os.path.join(folder, "predictions_temp.json")
                main_json = os.path.join(folder, "predictions.json")

                if os.path.exists(temp_json):
                    try:
                        with open(temp_json, "r", encoding="utf-8") as f:
                            temp_data = json.load(f)

                        if "images" in temp_data and isinstance(
                            self.existing_data, dict
                        ):
                            if "images" not in self.existing_data:
                                self.existing_data["images"] = []
                            self.existing_data["images"].extend(temp_data["images"])

                            with open(main_json, "w", encoding="utf-8") as f:
                                json.dump(self.existing_data, f, indent=1)

                            os.remove(temp_json)
                            self.logger.info(
                                f"Successfully merged {len(temp_data['images'])} resumed images into predictions.json"
                            )
                    except Exception as e:
                        self.logger.error(f"Error merging JSON files: {e}")
                        QMessageBox.warning(
                            self,
                            "Merge Error",
                            f"Failed to merge temporary JSON into main JSON: {e}",
                        )
                else:
                    self.logger.warning(
                        "Temporary JSON not found. SpeciesNet may have crashed or found no images to process."
                    )
            # --------------------

            if self.run_button and not self.run_button.isHidden():
                self.run_button.setEnabled(True)
            self.logger.info("SpeciesNet process finished")

            # Load images from the processed folder
            window = self.window()
            if window and hasattr(window, "load_folder_images") and folder:
                window.current_folder = folder
                window.load_folder_images()
                self.logger.info(f"Loaded images from processed folder: {folder}")
        except RuntimeError as e:
            self.logger.debug(f"Widget deleted during on_finished: {e}")
        except Exception as e:
            self.logger.error(f"Error in on_finished logic: {e}")
