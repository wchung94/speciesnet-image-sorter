"""
Utility functions for video frame extraction and processing.
Handles extracting frames from video files for processing with SpeciesNet.
"""

import concurrent.futures
import cv2
import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger("ImageViewer")

# Supported video formats
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm")


def get_video_files(folder_path):
    """
    Get all video files from a folder.

    Args:
        folder_path: Path to the folder

    Returns:
        List of video file paths sorted alphabetically
    """
    video_files = []
    if not os.path.isdir(folder_path):
        return video_files

    try:
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(VIDEO_EXTENSIONS):
                video_files.append(os.path.join(folder_path, filename))
    except Exception as e:
        logger.warning(f"Error reading video files from {folder_path}: {e}")

    return sorted(video_files)


def extract_frames(video_path, output_folder=None, frame_interval=30, max_frames=None):
    """
    Extract frames from a video file, skipping frames that are already extracted.

    Args:
        video_path: Path to the video file
        output_folder: Folder to save extracted frames (default: video_folder/video_name_frames)
        frame_interval: Extract every Nth frame (default: 30, which is ~1 frame per second at 30fps)
        max_frames: Maximum number of frames to extract (None = extract all)

    Returns:
        Dictionary with extraction results
    """
    try:
        # Open video file
        video = cv2.VideoCapture(video_path)
        if not video.isOpened():
            return {
                "success": False,
                "output_folder": None,
                "frame_count": 0,
                "message": f"Failed to open video: {video_path}",
            }

        # Get video info
        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        # Create output folder
        if output_folder is None:
            video_name = Path(video_path).stem
            video_folder = os.path.dirname(video_path)
            output_folder = os.path.join(video_folder, f"{video_name}_frames")

        os.makedirs(output_folder, exist_ok=True)

        # --- RESUME LOGIC ---
        # Look at the folder and find the last successfully saved frame number
        existing_files = [
            f for f in os.listdir(output_folder) if f.lower().endswith(".jpg")
        ]

        # Calculate how many frames were already extracted
        extracted_count = len(existing_files)

        # Reconstruct frame paths for existing files
        frame_paths = [os.path.join(output_folder, f) for f in sorted(existing_files)]

        if extracted_count > 0:
            logger.info(
                f"Resuming {Path(video_path).name}: Found {extracted_count} existing frames."
            )
            # We skip the frames we already processed
            frame_count = extracted_count * frame_interval
            # Fast-forward the video reader to the correct frame
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        else:
            frame_count = 0

        # --- EXTRACTION LOOP ---
        while True:
            ret, frame = video.read()
            if not ret:
                break

            # Extract frame if it matches the interval
            if frame_count % frame_interval == 0:
                if max_frames and extracted_count >= max_frames:
                    break

                # Save frame as image
                frame_filename = (
                    f"{Path(video_path).stem}_frame_{extracted_count:06d}.jpg"
                )
                frame_path = os.path.join(output_folder, frame_filename)

                # Double-check safety before overwriting
                if not os.path.exists(frame_path):
                    cv2.imwrite(frame_path, frame)
                    if frame_path not in frame_paths:
                        frame_paths.append(frame_path)

                extracted_count += 1

            frame_count += 1

        video.release()

        message = f"Done with {Path(video_path).name} (fps: {fps:.1f}, total frames: {total_frames}). Total saved: {extracted_count}."
        logger.info(message)

        return {
            "success": True,
            "output_folder": output_folder,
            "frame_count": extracted_count,
            "frame_paths": frame_paths,
            "message": message,
        }

    except Exception as e:
        logger.error(f"Error extracting frames from {video_path}: {e}")
        return {
            "success": False,
            "output_folder": None,
            "frame_count": 0,
            "message": f"Error extracting frames: {str(e)}",
        }


# --- TOP LEVEL WRAPPER (Must be outside to avoid Windows pickling errors) ---
def _process_video_wrapper(args):
    """Unpacks arguments and calls the main extraction function for a single CPU core."""
    video_file, frame_interval, max_frames_per_video = args
    return extract_frames(
        video_file,
        output_folder=None,
        frame_interval=frame_interval,
        max_frames=max_frames_per_video,
    )


def extract_frames_batch(
    video_files, output_base_folder=None, frame_interval=30, max_frames_per_video=None
):
    """
    Extract frames from multiple videos utilizing dynamic CPU scaling via ProcessPoolExecutor.
    Args:
        video_files: List of video file paths
        output_base_folder: Base folder to save extracted frames (default: same folder as videos)
        frame_interval: Extract every Nth frame (default: 30)
        max_frames_per_video: Maximum frames per video (None = extract all)

    Returns:
        List of dictionaries with extraction results
    """
    if not video_files:
        return []

    results = []

    # Dynamically determine the optimal number of workers
    available_cores = os.cpu_count() or 1

    # Windows OS hard limitation: ProcessPoolExecutor cannot exceed 61 workers
    if sys.platform == "win32":
        available_cores = min(available_cores, 61)

    optimal_workers = min(len(video_files), available_cores)

    logger.info(
        f"Starting parallel extraction using {optimal_workers} worker processes..."
    )

    # Package the arguments into tuples so they can be pickled and sent to other cores
    task_args = [(vf, frame_interval, max_frames_per_video) for vf in video_files]

    # Use ProcessPoolExecutor to run extractions in parallel
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=optimal_workers
    ) as executor:
        # map() submits the tasks to the wrapper function and guarantees results are returned in original order
        for result in executor.map(_process_video_wrapper, task_args):
            results.append(result)

    return results
