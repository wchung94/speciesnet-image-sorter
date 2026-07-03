"""
Utility functions for the Streamlit Image Sorter app.
"""

import streamlit as st
import os
import json
import subprocess
import sys
import shutil
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import filedialog

    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

IMAGE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
)

VIDEO_EXTENSIONS = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".flv",
    ".wmv",
    ".webm",
)

ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS


def is_video_file(path):
    """Return True if path is a supported video file."""
    return os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS


def log_message(message, level="INFO"):
    """Add a log message to the session state logs."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    st.session_state.logs.append(log_entry)
    # Keep only last 100 log entries
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]


def browse_folder():
    """Open a folder browser dialog using tkinter."""
    if not TKINTER_AVAILABLE:
        st.error("Folder browser not available. Please enter the path manually.")
        return None

    try:
        # Create a root window and hide it
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)

        # Open the folder dialog
        folder_path = filedialog.askdirectory(parent=root, title="Select a folder")

        root.destroy()

        return folder_path if folder_path else None
    except Exception as e:
        st.error(f"Error opening folder browser: {str(e)}")
        return None


def load_folder_images(folder_path):
    """Load all image and video files from the specified folder."""
    if not folder_path or not os.path.exists(folder_path):
        return []

    media_files = []

    try:
        for f in os.listdir(folder_path):
            if os.path.splitext(f)[1].lower() in ALL_MEDIA_EXTENSIONS:
                full_path = os.path.join(folder_path, f)
                if os.path.isfile(full_path):
                    media_files.append(full_path)

        media_files.sort()
        log_message(f"Loaded {len(media_files)} files from {folder_path}")
    except Exception as e:
        log_message(f"Error loading files: {str(e)}", "ERROR")

    return media_files


def copy_image_to_folder(image_path, destination_folder):
    """Copy an image to the destination folder."""
    if not destination_folder or not os.path.exists(destination_folder):
        log_message(f"Invalid destination folder: {destination_folder}", "ERROR")
        st.error(f"Invalid destination folder: {destination_folder}")
        return False

    try:
        os.makedirs(destination_folder, exist_ok=True)
        destination = os.path.join(destination_folder, os.path.basename(image_path))
        shutil.copy(image_path, destination)
        log_message(f"Copied {os.path.basename(image_path)} to {destination_folder}")
        st.success(f"✓ Copied to {os.path.basename(destination_folder)}")
        return True
    except Exception as e:
        log_message(f"Failed to copy image: {str(e)}", "ERROR")
        st.error(f"Failed to copy image: {str(e)}")
        return False


def rename_megadetector_output(folder_path):
    """Rename MegaDetector output files to have _pred suffix.

    Renames files so only the part after the last '~' remains,
    and adds a '_pred' postfix before the extension.
    """
    if not os.path.isdir(folder_path):
        log_message(f"Folder not found for renaming: {folder_path}", "WARNING")
        return

    try:
        files = [
            f
            for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]
        renamed_count = 0

        for filename in files:
            # Check if file contains '~' (MegaDetector output indicator)
            if "~" not in filename:
                continue

            # Extract the part after the last '~'
            parts = filename.split("~")
            if len(parts) < 2:
                continue

            base_name = parts[-1]  # Everything after last ~
            name_without_ext, ext = os.path.splitext(base_name)

            # Add _pred suffix before extension
            new_name = f"{name_without_ext}_pred{ext}"

            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_name)

            # If target exists, add numeric suffix
            counter = 1
            while os.path.exists(new_path):
                new_name = f"{name_without_ext}_pred_{counter}{ext}"
                new_path = os.path.join(folder_path, new_name)
                counter += 1

            # Rename the file
            os.rename(old_path, new_path)
            renamed_count += 1
            log_message(f"Renamed: {filename} -> {new_name}")

        if renamed_count > 0:
            log_message(f"Renamed {renamed_count} MegaDetector output files")
    except Exception as e:
        log_message(f"Error renaming MegaDetector output: {str(e)}", "ERROR")


def _extract_video_frames(folder_path):
    """Extract frames from all videos in the folder. Returns list of frame folders."""
    try:
        # Import lazily to avoid hard dependency when not needed
        import sys as _sys

        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _root not in _sys.path:
            _sys.path.insert(0, _root)

        from pyqt_app.video_utils import get_video_files, extract_frames
    except ImportError:
        log_message(
            "video_utils not available; skipping video frame extraction", "WARNING"
        )
        return []

    video_files = get_video_files(folder_path)
    if not video_files:
        return []

    log_message(f"Found {len(video_files)} video file(s); extracting frames...")
    extracted_folders = []
    for video_file in video_files:
        result = extract_frames(video_file, frame_interval=30)
        if result["success"]:
            log_message(f"✓ {result['message']}")
            extracted_folders.append(result["output_folder"])
        else:
            log_message(f"✗ {result['message']}", "WARNING")
    return extracted_folders


def run_speciesnet(folder_path):
    """Run SpeciesNet on the selected folder."""
    if not folder_path or not os.path.exists(folder_path):
        log_message("Invalid folder path for SpeciesNet", "ERROR")
        st.error("Invalid folder path")
        return False

    predictions_json = os.path.join(folder_path, "predictions.json")
    filepaths_txt = os.path.join(folder_path, "speciesnet_filepaths.txt")

    # Extract video frames first
    extracted_frame_folders = _extract_video_frames(folder_path)

    # Collect image files from main folder and extracted frame folders
    image_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        and os.path.isfile(os.path.join(folder_path, f))
    ]
    for frame_folder in extracted_frame_folders:
        image_files.extend(
            os.path.join(frame_folder, f)
            for f in os.listdir(frame_folder)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
            and os.path.isfile(os.path.join(frame_folder, f))
        )
    # Deduplicate while preserving order
    image_files = list(dict.fromkeys(image_files))

    if not image_files:
        log_message("No image files found in folder", "WARNING")
        st.warning("No image files found in folder")
        return False

    try:
        log_message(f"Running SpeciesNet on {folder_path}...")
        with st.spinner(
            "Running SpeciesNet inference... This may take several minutes."
        ):
            # Write filepaths to a text file to avoid command-line length limits
            with open(filepaths_txt, "w", encoding="utf-8") as fh:
                fh.write("\n".join(image_files))

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

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=folder_path
            )

            if result.returncode == 0:
                log_message("SpeciesNet completed successfully")
                st.success("✓ SpeciesNet completed successfully!")

                # Load predictions data
                if os.path.exists(predictions_json):
                    with open(predictions_json, "r") as f:
                        st.session_state.predictions_data = json.load(f)
                        st.session_state.show_predictions = True

                return True
            else:
                log_message(f"SpeciesNet failed: {result.stderr}", "ERROR")
                st.error(f"SpeciesNet failed: {result.stderr}")
                return False

    except Exception as e:
        log_message(f"Error running SpeciesNet: {str(e)}", "ERROR")
        st.error(f"Error running SpeciesNet: {str(e)}")
        return False


def run_megadetector(folder_path):
    """Run MegaDetector visualization on the selected folder."""
    if not folder_path or not os.path.exists(folder_path):
        log_message("Invalid folder path for MegaDetector", "ERROR")
        st.error("Invalid folder path")
        return False

    predictions_json = os.path.join(folder_path, "predictions.json")
    if not os.path.isfile(predictions_json):
        log_message(f"No predictions.json found in {folder_path}", "WARNING")
        st.warning("No predictions.json found. Please run SpeciesNet first.")
        return False

    try:
        log_message(f"Running MegaDetector visualization on {folder_path}...")
        with st.spinner(
            "Running MegaDetector visualization... This may take a few minutes."
        ):
            output_dir = folder_path

            cmd = [
                "python",
                "-m",
                "megadetector.visualization.visualize_detector_output",
                predictions_json,
                output_dir,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=folder_path
            )

            if result.returncode == 0:
                log_message("MegaDetector visualization completed successfully")

                # Rename output files with _pred suffix
                rename_megadetector_output(folder_path)

                st.success("✓ MegaDetector visualization completed!")
                # Reload images to show new visualizations
                st.session_state.image_files = load_folder_images(folder_path)
                return True
            else:
                log_message(f"MegaDetector failed: {result.stderr}", "ERROR")
                st.error(f"MegaDetector failed: {result.stderr}")
                return False

    except Exception as e:
        log_message(f"Error running MegaDetector: {str(e)}", "ERROR")
        st.error(f"Error running MegaDetector: {str(e)}")
        return False


def display_predictions_info():
    """Display predictions information if available."""
    if st.session_state.predictions_data and st.session_state.show_predictions:
        current_file = st.session_state.image_files[
            st.session_state.current_image_index
        ]
        filename = os.path.basename(current_file)

        # Find prediction for current image
        for pred in st.session_state.predictions_data.get("images", []):
            if pred.get("file", "").endswith(filename):
                st.subheader("🔍 Detection Results")

                detections = pred.get("detections", [])
                if detections:
                    for i, det in enumerate(detections, 1):
                        category = det.get("category", "unknown")
                        conf = det.get("conf", 0)

                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Detection {i}:** {category}")
                        with col2:
                            st.write(f"Confidence: {conf:.2%}")

                        # Show class probabilities if available
                        class_probs = det.get("class_probs", {})
                        if class_probs:
                            with st.expander("View all species probabilities"):
                                sorted_probs = sorted(
                                    class_probs.items(),
                                    key=lambda x: x[1],
                                    reverse=True,
                                )
                                for species, prob in sorted_probs[:10]:  # Show top 10
                                    st.write(f"{species}: {prob:.2%}")
                else:
                    st.info("No detections found in this image")
                break
