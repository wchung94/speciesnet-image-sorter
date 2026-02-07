#!/usr/bin/env python3
"""
Streamlit application entry point.
Can be run with: streamlit run streamlit_main.py
Or: uv run streamlit run streamlit_main.py
"""

import streamlit as st
import os
from pathlib import Path
import json
import subprocess
import logging
import shutil
from io import BytesIO
from PIL import Image

import sys
import tempfile


# Try to import Databricks SDK for volume access
try:
    from databricks.sdk import WorkspaceClient
    DATABRICKS_SDK_AVAILABLE = True
except ImportError:
    DATABRICKS_SDK_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StreamlitApp")

# Page config
st.set_page_config(
    page_title="Simple Image Sorter",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Utility functions
def copy_current_image_to_new_folder(new_folder_path, image_files, current_image_index):
    """Copy the current image to the selected new folder."""
    if new_folder_path and image_files:
        current_image_file = image_files[current_image_index]
        destination = os.path.join(new_folder_path, os.path.basename(current_image_file))
        shutil.copy(current_image_file, destination)
        logger.info(f"Copied {current_image_file} to {destination}")


def run_speciesnet(folder_path):
    """Run SpeciesNet on a folder; supports Databricks Volumes by staging to a local temp dir."""
    try:
        # 1) List with your existing helper (works for /Volumes and local)
        files = list_folder_files(folder_path)

        # 2) Filter to image extensions SpeciesNet/YOLOv5 can handle
        valid_exts = {".jpg", ".jpeg", ".png", ".bmp"}
        image_names = [f for f in files if os.path.splitext(f)[1].lower() in valid_exts]
        if not image_names:
            raise Exception("No image files (.jpg/.jpeg/.png/.bmp) found in folder")

        # 3) Stage to a local temp dir if /Volumes/; else use folder directly
        is_volumes = folder_path.startswith("/Volumes/")
        work_dir = folder_path
        staged = []

        if is_volumes and DATABRICKS_SDK_AVAILABLE:
            client = WorkspaceClient()
            work_dir = tempfile.mkdtemp(prefix="speciesnet_")
            for name in image_names:
                src = os.path.join(folder_path, name)
                dst = os.path.join(work_dir, name)
                # Read with your SDK-aware reader
                data = read_image_bytes(src)
                with open(dst, "wb") as f:
                    f.write(data)
                staged.append(dst)
        else:
            # regular local paths
            staged = [os.path.join(folder_path, n) for n in image_names]

        # 4) Build filepaths argument for SpeciesNet (comma-separated paths)
        filepaths_arg = ",".join(staged)

        # 5) Predictions output path
        local_predictions = os.path.join(work_dir, "predictions.json")

        # 6) Run SpeciesNet with the SAME interpreter as Streamlit
        cmd = [
            sys.executable, "-m", "speciesnet.scripts.run_model",
            "--filepaths", filepaths_arg,
            "--predictions_json", local_predictions,
            "country", "NL"
        ]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if process.returncode != 0:
            raise Exception(f"SpeciesNet failed: {process.stderr.strip()}")

        logger.info(f"SpeciesNet completed successfully in {work_dir}")

        # 7) If staged, upload predictions.json back to the original /Volumes folder
        if is_volumes and DATABRICKS_SDK_AVAILABLE:
            target = os.path.join(folder_path, "predictions.json")
            try:
                client = WorkspaceClient()
                with open(local_predictions, "rb") as f:
                    client.files.upload(target, f.read(), overwrite=True)
                logger.info(f"Uploaded predictions.json to {target}")
            except Exception as e:
                logger.error(f"Failed to upload predictions.json to {target}: {e}")
                raise

    except Exception as e:
        logger.error(f"Error running SpeciesNet: {str(e)}")
        raise


def run_megadetector(folder_path):
    """Run MegaDetector on both local disk and Databricks /Volumes by staging to a local temp folder."""
    try:
        is_volumes = folder_path.startswith("/Volumes/") and DATABRICKS_SDK_AVAILABLE

        # 1. Determine staging directory
        work_dir = folder_path
        if is_volumes:
            work_dir = tempfile.mkdtemp(prefix="megadetector_")
            client = WorkspaceClient()

            # --- Copy predictions.json ---
            src_pred = os.path.join(folder_path, "predictions.json")
            try:
                resp = client.files.download(src_pred)
                stream = resp.contents
                if hasattr(stream, "iter_bytes"):
                    data = b"".join(chunk for chunk in stream.iter_bytes() if chunk)
                else:
                    data = stream.read()
                with open(os.path.join(work_dir, "predictions.json"), "wb") as f:
                    f.write(data)
            except Exception:
                raise Exception(f"predictions.json not found in {folder_path}")

            # --- Copy original images to staging dir ---
            files = list_folder_files(folder_path)
            for fname in files:
                if os.path.splitext(fname)[1].lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
                    continue
                src = os.path.join(folder_path, fname)
                dst = os.path.join(work_dir, fname)
                img_bytes = read_image_bytes(src)
                with open(dst, "wb") as f:
                    f.write(img_bytes)

        # 2. Run MegaDetector in the staging (or original) folder
        pred_json_local = os.path.join(work_dir, "predictions.json")
        if not os.path.exists(pred_json_local):
            raise Exception(f"predictions.json missing in working folder: {work_dir}")

        cmd = [
            sys.executable, "-m",
            "megadetector.visualization.visualize_detector_output",
            pred_json_local,
            work_dir
        ]

        process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if process.returncode != 0:
            raise Exception(f"MegaDetector failed: {process.stderr.strip()}")

        # 3. Rename MD outputs in the staging folder
        rename_megadetector_outputs(work_dir)

        logger.info(f"MegaDetector completed successfully in {work_dir}")

        # 4. Upload results back to /Volumes
        if is_volumes:
            client = WorkspaceClient()

            for fname in os.listdir(work_dir):
                if fname.endswith("_bb.jpg") or fname.endswith("_bb.jpeg") or fname.endswith("_bb.png"):
                    local_file = os.path.join(work_dir, fname)
                    remote_file = os.path.join(folder_path, fname)
                    with open(local_file, "rb") as f:
                        client.files.upload(remote_file, f.read(), overwrite=True)

            logger.info(f"Uploaded all MegaDetector outputs back to {folder_path}")

    except Exception as e:
        logger.error(f"Error running MegaDetector: {str(e)}")
        raise


import sys
import tempfile
import time

def run_megadetector(folder_path):
    """Run MegaDetector on both local disk and Databricks /Volumes by staging to a local temp folder,
    then upload only the true bounding-box files back to the volume."""
    try:
        is_volumes = folder_path.startswith("/Volumes/") and DATABRICKS_SDK_AVAILABLE

        # 1) Stage inputs (predictions.json + images) if /Volumes/
        work_dir = folder_path
        if is_volumes:
            work_dir = tempfile.mkdtemp(prefix="megadetector_")
            client = WorkspaceClient()

            # --- Copy predictions.json ---
            src_pred = os.path.join(folder_path, "predictions.json")
            try:
                resp = client.files.download(src_pred)
                stream = resp.contents
                if hasattr(stream, "iter_bytes"):
                    data = b"".join(chunk for chunk in stream.iter_bytes() if chunk)
                else:
                    data = stream.read()
                with open(os.path.join(work_dir, "predictions.json"), "wb") as f:
                    f.write(data)
            except Exception:
                raise Exception(f"predictions.json not found in {folder_path}")

            # --- Copy original images to staging dir ---
            files = list_folder_files(folder_path)
            for fname in files:
                if os.path.splitext(fname)[1].lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
                    continue
                src = os.path.join(folder_path, fname)
                dst = os.path.join(work_dir, fname)
                img_bytes = read_image_bytes(src)
                with open(dst, "wb") as f:
                    f.write(img_bytes)

        # 2) Snapshot BEFORE state (to detect new/overwritten outputs)
        pred_json_local = os.path.join(work_dir, "predictions.json")
        if not os.path.exists(pred_json_local):
            raise Exception(f"predictions.json missing in working folder: {work_dir}")

        image_exts = {".jpg", ".jpeg", ".png", ".bmp"}
        before_files = [
            f for f in os.listdir(work_dir)
            if os.path.isfile(os.path.join(work_dir, f)) and os.path.splitext(f)[1].lower() in image_exts
        ]
        before_stats = {
            f: os.path.getmtime(os.path.join(work_dir, f))
            for f in before_files
        }

        md_start = time.time()

        # 3) Run MegaDetector
        cmd = [
            sys.executable, "-m",
            "megadetector.visualization.visualize_detector_output",
            pred_json_local,
            work_dir
        ]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if process.returncode != 0:
            raise Exception(f"MegaDetector failed: {process.stderr.strip()}")

        # 4) Snapshot AFTER state
        after_files = [
            f for f in os.listdir(work_dir)
            if os.path.isfile(os.path.join(work_dir, f)) and os.path.splitext(f)[1].lower() in image_exts
        ]
        before_set = set(before_files)
        after_set = set(after_files)

        # New files created by MD (separate outputs)
        new_files = sorted(list(after_set - before_set))

        # Overwritten files (mtime increased after MD start)
        overwritten = []
        for f in before_files:
            p = os.path.join(work_dir, f)
            try:
                if os.path.getmtime(p) > md_start + 0.001:  # small epsilon
                    overwritten.append(f)
                # else unchanged original
            except OSError:
                pass

        logger.info(f"MD new files: {new_files}")
        logger.info(f"MD overwritten files: {overwritten}")

        # 5) Normalize names of new outputs → *_bb.ext
        bb_from_new = rename_megadetector_outputs(work_dir, only_these=new_files)

        # 6) For overwritten originals, DUPLICATE to *_bb.ext (we never upload originals)
        bb_from_overwrite = []
        for f in overwritten:
            src = os.path.join(work_dir, f)
            base, ext = os.path.splitext(f)
            # build unique *_bb.ext name
            cand = f"{base}_bb{ext}"
            dst = os.path.join(work_dir, cand)
            counter = 1
            while os.path.exists(dst):
                cand = f"{base}_bb_{counter}{ext}"
                dst = os.path.join(work_dir, cand)
                counter += 1
            shutil.copy2(src, dst)
            bb_from_overwrite.append(os.path.basename(dst))
            logger.info(f"Duplicated overwritten MD output: {f} → {os.path.basename(dst)}")

        # Union of all _bb outputs to upload
        bb_files = bb_from_new + bb_from_overwrite

        logger.info(f"Final _bb files to upload: {bb_files}")

        # 7) Upload back to /Volumes
        if is_volumes:
            client = WorkspaceClient()
            for fname in bb_files:
                local_file = os.path.join(work_dir, fname)
                remote_file = os.path.join(folder_path, fname)
                with open(local_file, "rb") as f:
                    client.files.upload(remote_file, f.read(), overwrite=True)
            logger.info(f"Uploaded {len(bb_files)} bounding-box images to {folder_path}")

    except Exception as e:
        logger.error(f"Error running MegaDetector: {str(e)}")
        raise


def rename_megadetector_outputs(folder_path, only_these=None):
    """
    Normalize MegaDetector output files to *_bb.<ext>.
    Only renames REAL MegaDetector outputs (never originals).
    Returns a list of produced *_bb files.
    If only_these is provided, only consider those filenames.
    """
    produced_bb = []
    try:
        candidates = only_these if only_these is not None else os.listdir(folder_path)
        for fname in candidates:
            src = os.path.join(folder_path, fname)
            if not os.path.isfile(src):
                continue

            base, ext = os.path.splitext(fname)
            ext_l = ext.lower()

            # Skip non-image outputs
            if ext_l not in {".jpg", ".jpeg", ".png"}:
                continue

            new_base = None

            # 1) Old TF MD "~" pattern
            if "~" in fname:
                original = fname.split("~")[-1].strip()
                obase, oext = os.path.splitext(original)
                new_base, out_ext = f"{obase}_bb", oext

            # 2) YOLO MD: *_md.<ext>
            elif base.endswith("_md"):
                clean = base[:-3]
                new_base, out_ext = f"{clean}_bb", ext

            # 3) YOLO MD: name.ext_md.ext  (where ext_l still equals the true extension)
            elif "_md" in base:
                clean = base.replace("_md", "")
                new_base, out_ext = f"{clean}_bb", ext

            # 4) md_* prefix
            elif base.startswith("md_"):
                clean = base[3:]
                new_base, out_ext = f"{clean}_bb", ext

            else:
                # ORIGINAL or unknown pattern; skip
                continue

            # Build destination with proper collision handling
            dst = os.path.join(folder_path, f"{new_base}{out_ext}")
            counter = 1
            while os.path.exists(dst):
                dst = os.path.join(folder_path, f"{new_base}_{counter}{out_ext}")
                counter += 1

            os.rename(src, dst)
            produced_bb.append(os.path.basename(dst))
            logger.info(f"Renamed MD output: {fname} → {os.path.basename(dst)}")

    except Exception as e:
        logger.error(f"Error renaming MegaDetector outputs: {e}")

    return produced_bb

# Initialize session state
if "current_folder" not in st.session_state:
    st.session_state.current_folder = None
if "image_files" not in st.session_state:
    st.session_state.image_files = []
if "current_image_index" not in st.session_state:
    st.session_state.current_image_index = 0
if "folder_paths" not in st.session_state:
    st.session_state.folder_paths = {
        "folder_1": None,
        "folder_2": None,
        "folder_3": None,
    }
if "show_predictions" not in st.session_state:
    st.session_state.show_predictions = False

# Sidebar for folder selection and configuration
st.sidebar.title("Configuration")

# Main folder selection
st.sidebar.subheader("📁 Source Folder")
st.sidebar.markdown("""
**Enter the full path to your image folder:**

Examples:
- `/Users/wingchung/Documents/repos/SimpleImageSorter/demo_images`
- `/home/user/images/animals`
- `C:\\Users\\YourName\\Pictures\\wildlife` (Windows)
- `/Volumes/users/wy_chung/demo_volume` (Databricks)
""")

def is_valid_folder(folder_path):
    """Check if folder exists, supporting both local and Databricks paths."""
    if not folder_path or not folder_path.strip():
        return False
        
    folder_path = folder_path.strip()
    
    try:
        # Check if it's a Databricks volume path
        if folder_path.startswith("/Volumes/"):
            logger.info(f"Detected Databricks volume path: {folder_path}")
            
            # Try using WorkspaceClient first (for Databricks Apps)
            if DATABRICKS_SDK_AVAILABLE:
                try:
                    client = WorkspaceClient()
                    # Use the SDK to list directory contents
                    result = list(client.files.list_directory_contents(folder_path))
                    logger.info(f"Databricks volume path validated via SDK: {folder_path} (found {len(result)} items)")
                    return True
                except Exception as e:
                    logger.error(f"SDK validation failed for {folder_path}: {type(e).__name__} - {str(e)}")
            
            # Try filesystem access as fallback (for local development)
            try:
                files = os.listdir(folder_path)
                logger.info(f"Databricks volume path validated via filesystem: {folder_path}")
                return True
            except Exception as e:
                logger.warning(f"Filesystem access also failed for {folder_path}: {e}")
            
            logger.error(f"Could not validate Databricks volume path: {folder_path} (neither SDK nor filesystem worked)")
            return False
            
        # Check for legacy /mnt/ paths (DBMount)
        elif folder_path.startswith("/mnt/"):
            logger.info(f"Detected DBMount path: {folder_path}")
            try:
                files = os.listdir(folder_path)
                logger.info(f"DBMount path validated: {folder_path}")
                return True
            except Exception as e:
                logger.error(f"DBMount path not accessible: {folder_path}")
                return False
        
        # Regular local path
        else:
            logger.info(f"Checking local path: {folder_path}")
            is_valid = os.path.isdir(folder_path)
            if is_valid:
                logger.info(f"Local path validated: {folder_path}")
            else:
                logger.error(f"Local path not found: {folder_path}")
            return is_valid
            
    except Exception as e:
        logger.error(f"Unexpected error validating folder {folder_path}: {type(e).__name__} - {str(e)}")
        return False


def list_folder_files(folder_path):
    """List files in folder, supporting both local and Databricks paths."""
    try:
        # Check if it's a Databricks volume path
        if folder_path.startswith("/Volumes/"):
            logger.info(f"Listing files from Databricks volume: {folder_path}")
            
            if DATABRICKS_SDK_AVAILABLE:
                try:
                    client = WorkspaceClient()
                    items = client.files.list_directory_contents(folder_path)
                    
                    files = []
                    all_items_debug = []
                    
                    for item in items:
                        logger.debug(f"Raw SDK item: {item}")
                        logger.debug(f"Item type: {type(item).__name__}")
                        
                        # Check if it's an ObjectInfo with path attribute
                        if hasattr(item, 'path'):
                            full_path = item.path
                            # Extract just the filename
                            filename = os.path.basename(full_path)
                            
                            # Check if it's a file (not a directory)
                            is_file = True
                            if hasattr(item, 'object_type'):
                                object_type = str(item.object_type)
                                logger.debug(f"Object type: {object_type}")
                                is_file = 'FILE' in object_type.upper()
                            
                            logger.info(f"Item: {filename}, is_file: {is_file}, full_path: {full_path}")
                            
                            if is_file:
                                files.append(filename)
                                all_items_debug.append(f"{filename} (FILE)")
                            else:
                                all_items_debug.append(f"{filename} (DIR)")
                        else:
                            # Fallback
                            str_repr = str(item)
                            logger.debug(f"String representation: {str_repr}")
                            filename = str_repr.split('/')[-1]
                            if filename:
                                files.append(filename)
                                all_items_debug.append(filename)
                    
                    logger.info(f"Listed {len(files)} FILES (out of {len(all_items_debug)} total items)")
                    logger.info(f"All items: {all_items_debug}")
                    return files
                    
                except Exception as e:
                    logger.error(f"SDK file listing failed for {folder_path}: {type(e).__name__} - {e}", exc_info=True)
                    # Fall through to filesystem attempt
        
        # For local paths or fallback
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        logger.info(f"Listed {len(files)} files from local path {folder_path}")
        return files
        
    except Exception as e:
        logger.error(f"Error listing files in {folder_path}: {e}", exc_info=True)
        raise

def read_image_bytes(image_path: str) -> bytes:
    """Read image bytes from local filesystem or Databricks /Volumes using the SDK's StreamingResponse."""
    try:
        # Databricks Volume path
        if image_path.startswith("/Volumes/") and DATABRICKS_SDK_AVAILABLE:
            client = WorkspaceClient()
            resp = client.files.download(image_path)

            stream = resp.contents  # In your SDK: contents is a StreamingResponse, NOT bytes

            # Preferred: iter_bytes() (safe for large files)
            if hasattr(stream, "iter_bytes"):
                buf = bytearray()
                for chunk in stream.iter_bytes():
                    if chunk:
                        buf.extend(chunk)
                return bytes(buf)

            # Fallback: raw read()
            if hasattr(stream, "read"):
                return stream.read()

            raise RuntimeError("StreamingResponse contained no readable content")

        # Local filesystem
        with open(image_path, "rb") as f:
            return f.read()

    except Exception as e:
        logger.error(f"Error reading image {image_path}: {type(e).__name__} - {e}", exc_info=True)
        raise


selected_folder = st.sidebar.text_input(
    "Folder path:",
    value=st.session_state.current_folder or "",
    placeholder="/path/to/images"
)

# Add Load Folder button
if st.sidebar.button("📂 Load Folder", use_container_width=True):
    logger.info(f"🔘 Load Folder button clicked with path: {selected_folder}")
    if not selected_folder:
        st.error("❌ Please enter a folder path")
        logger.warning("Load button clicked but path is empty")
    elif is_valid_folder(selected_folder):
        st.session_state.current_folder = selected_folder
        logger.info(f"✓ Folder validation passed. Starting image loading from: {selected_folder}")
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        try:
            logger.info(f"About to call list_folder_files for: {selected_folder}")
            files = list_folder_files(selected_folder)
            logger.info(f"✓ list_folder_files returned {len(files)} files")
            image_files = []
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in image_extensions:
                    full_path = os.path.join(selected_folder, f)
                    image_files.append(full_path)
                    logger.info(f"✓ Added image: {f} (extension: {ext})")
            image_files = sorted(image_files)
            st.session_state.image_files = image_files
            st.session_state.current_image_index = 0
            if image_files:
                st.success(f"✅ Loaded {len(image_files)} images from {selected_folder}")
            else:
                st.warning(f"⚠️ No image files found in {selected_folder}")
        except Exception as e:
            st.error(f"❌ Error loading images: {str(e)}")
            logger.error(f"❌ Exception during image loading: {str(e)}", exc_info=True)
    else:
        st.error(f"❌ Invalid folder path: `{selected_folder}`")


# Configure destination folders
st.sidebar.subheader("📂 Destination Folders")
for i in range(1, 4):
    folder_key = f"folder_{i}"
    st.session_state.folder_paths[folder_key] = st.sidebar.text_input(
        f"Folder {i} path:",
        value=st.session_state.folder_paths[folder_key] or "",
        key=f"input_{folder_key}"
    )
    
    # Create folder if it doesn't exist
    if st.session_state.folder_paths[folder_key]:
        Path(st.session_state.folder_paths[folder_key]).mkdir(parents=True, exist_ok=True)

# AI Features in sidebar
st.sidebar.subheader("🤖 AI Features")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Run SpeciesNet"):
        if st.session_state.current_folder:
            with st.spinner("Running SpeciesNet..."):
                try:
                    run_speciesnet(st.session_state.current_folder)
                    st.success("✅ SpeciesNet completed!")
                except Exception as e:
                    st.error(f"❌ Error running SpeciesNet: {str(e)}")
        else:
            st.warning("⚠️ Please select a folder first")

with col2:
    if st.button("Run MegaDetector"):
        if st.session_state.current_folder:
            with st.spinner("Running MegaDetector..."):
                try:
                    run_megadetector(st.session_state.current_folder)
                    st.success("✅ MegaDetector completed!")
                except Exception as e:
                    st.error(f"❌ Error running MegaDetector: {str(e)}")
        else:
            st.warning("⚠️ Please select a folder first")

# Main content area
st.title("🖼️ WildlifeCam 2025 V0.1 - SpeciesNet - Ch.Chung")


if not st.session_state.image_files:
    st.info("👈 Please select a folder containing images using the sidebar")
else:
    # Display image counter
    st.write(f"Image {st.session_state.current_image_index + 1} of {len(st.session_state.image_files)}")
    
    # Get current image
    current_image_path = st.session_state.image_files[st.session_state.current_image_index]
    current_image_name = os.path.basename(current_image_path)
    
    # Display image
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # In your display section:
        try:
            image_bytes = read_image_bytes(current_image_path)
            img = Image.open(BytesIO(image_bytes))
            # Optionally, call img.load() to force decode here and surface errors early
            img.load()
            st.image(img, use_column_width=True)
            st.caption(current_image_name)
        except Exception as e:
            st.error(f"❌ Could not display image: {str(e)}")
            logger.error(f"Failed to display {current_image_path}: {e}")


    with col2:
        st.subheader("Image Info")
        st.write(f"**Name:** {current_image_name}")
        st.write(f"**Index:** {st.session_state.current_image_index + 1}/{len(st.session_state.image_files)}")
    
    # Check for predictions.json
    predictions_path = os.path.join(st.session_state.current_folder, "predictions.json")
    if os.path.exists(predictions_path):
        st.sidebar.subheader("📊 Predictions")
        try:
            with open(predictions_path, 'r') as f:
                predictions = json.load(f)
                # Find prediction for current image
                image_name = os.path.basename(current_image_path)
                if image_name in predictions:
                    pred = predictions[image_name]
                    st.sidebar.write(f"**Species:** {pred.get('species', 'Unknown')}")
                    st.sidebar.write(f"**Confidence:** {pred.get('confidence', 'N/A')}")
        except:
            pass
    
    # Navigation controls
    st.divider()
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    
    with nav_col1:
        if st.button("⬅️ Previous", use_container_width=True):
            st.session_state.current_image_index = (st.session_state.current_image_index - 1) % len(st.session_state.image_files)
            st.rerun()
    
    with nav_col2:
        st.write("")  # Spacer
    
    with nav_col3:
        if st.button("Next ➡️", use_container_width=True):
            st.session_state.current_image_index = (st.session_state.current_image_index + 1) % len(st.session_state.image_files)
            st.rerun()
    
    # Sorting buttons
    st.divider()
    st.subheader("📋 Copy to Folder")
    
    sort_cols = st.columns(3)
    for i in range(1, 4):
        with sort_cols[i-1]:
            folder_key = f"folder_{i}"
            folder_path = st.session_state.folder_paths[folder_key]
            
            if folder_path and folder_path.strip():
                folder_name = os.path.basename(folder_path) or folder_path
                if st.button(f"📌 Copy to Folder {i}\n({folder_name})", use_container_width=True):
                    try:
                        copy_current_image_to_new_folder(
                            folder_path,
                            st.session_state.image_files,
                            st.session_state.current_image_index
                        )
                        st.success(f"✅ Copied to Folder {i}")
                        # Auto-advance to next image
                        st.session_state.current_image_index = (st.session_state.current_image_index + 1) % len(st.session_state.image_files)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error copying image: {str(e)}")
            else:
                st.button(f"Folder {i}\n(Not configured)", use_container_width=True, disabled=True)
    
    # Image thumbnail list
    st.divider()
    st.subheader("📸 Image List")
    
    # Create columns for thumbnail grid
    cols = st.columns(6)
    for idx, image_path in enumerate(st.session_state.image_files):
        col = cols[idx % 6]
        with col:
            # Use smaller thumbnail
            try:
                image_bytes = read_image_bytes(image_path)
                thumb = Image.open(BytesIO(image_bytes))
                thumb.load()
                st.image(thumb, width=80)
                if st.button(f"{idx + 1}", key=f"thumb_{idx}", use_container_width=True):
                    st.session_state.current_image_index = idx
                    st.rerun()
            except Exception as e:
                logger.warning(f"Thumbnail failed for {image_path}: {e}")
                st.write(f"❌ {idx + 1}")
