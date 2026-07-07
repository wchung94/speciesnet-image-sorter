"""
Utility functions for video frame extraction and processing.
Handles extracting frames from video files for processing with SpeciesNet.
"""

import cv2
import os
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
    Extract frames from a video file.

    Args:
        video_path: Path to the video file
        output_folder: Folder to save extracted frames (default: video_folder/video_name_frames)
        frame_interval: Extract every Nth frame (default: 30, which is ~1 frame per second at 30fps)
        max_frames: Maximum number of frames to extract (None = extract all)

    Returns:
        Dictionary with:
            - 'success': bool indicating if extraction succeeded
            - 'output_folder': path to folder with extracted frames
            - 'frame_count': number of frames extracted
            - 'message': status/error message
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

        # Extract frames
        frame_count = 0
        extracted_count = 0
        frame_paths = []

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
                cv2.imwrite(frame_path, frame)
                frame_paths.append(frame_path)
                extracted_count += 1

            frame_count += 1

        video.release()

        message = f"Extracted {extracted_count} frames from {Path(video_path).name} (fps: {fps:.1f}, total frames: {total_frames})"
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


def extract_frames_batch(
    video_files, output_base_folder=None, frame_interval=30, max_frames_per_video=None
):
    """
    Extract frames from multiple videos.

    Args:
        video_files: List of video file paths
        output_base_folder: Base folder to save extracted frames (default: same folder as videos)
        frame_interval: Extract every Nth frame (default: 30)
        max_frames_per_video: Maximum frames per video (None = extract all)

    Returns:
        List of dictionaries with extraction results
    """
    results = []
    for video_file in video_files:
        result = extract_frames(
            video_file,
            output_folder=None,  # Let each video create its own frames folder
            frame_interval=frame_interval,
            max_frames=max_frames_per_video,
        )
        results.append(result)

    return results
