"""
Streamlit Image Sorter with SpeciesNet and MegaDetector
A web-based version of the SpeciesNetImageSorter PyQt application.
"""
import streamlit as st
import os
import json
from PIL import Image
from streamlit_utils import (
    log_message,
    browse_folder,
    load_folder_images,
    copy_image_to_folder,
    run_speciesnet,
    run_megadetector,
    display_predictions_info
)

# Configure page
st.set_page_config(
    page_title="SpeciesNet Image Sorter",
    page_icon="🦌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "current_folder" not in st.session_state:
    st.session_state.current_folder = None
if "image_files" not in st.session_state:
    st.session_state.image_files = []
if "current_image_index" not in st.session_state:
    st.session_state.current_image_index = 0
if "folder_1" not in st.session_state:
    st.session_state.folder_1 = None
if "folder_2" not in st.session_state:
    st.session_state.folder_2 = None
if "folder_3" not in st.session_state:
    st.session_state.folder_3 = None
if "logs" not in st.session_state:
    st.session_state.logs = []
if "show_predictions" not in st.session_state:
    st.session_state.show_predictions = False
if "predictions_data" not in st.session_state:
    st.session_state.predictions_data = None




# Main UI
st.title("SpeciesNet Image Sorter")
st.markdown("---")

# Sidebar for folder selection and configuration
with st.sidebar:
    st.header("📁 Folder Settings")
    
    # Display current folder path (read-only display)
    if st.session_state.current_folder:
        st.info(f"📂 Current folder: {st.session_state.current_folder}")
    else:
        st.info("📂 No folder loaded yet")
    
    if st.button("📂 Load Folder", use_container_width=True):
        # Open file explorer to select folder
        selected_folder = browse_folder()
        
        # If user selected a folder from the dialog, use it
        if selected_folder:
            st.session_state.current_folder = selected_folder
            st.session_state.image_files = load_folder_images(selected_folder)
            st.session_state.current_image_index = 0
            
            # Show feedback about loaded images
            if len(st.session_state.image_files) == 0:
                st.warning(f"No images found in {selected_folder}")
                log_message(f"No images found in folder: {selected_folder}", "WARNING")
            else:
                st.success(f"✓ Loaded {len(st.session_state.image_files)} images")
                log_message(f"Loaded {len(st.session_state.image_files)} images from: {selected_folder}")
            
            # Check for predictions.json
            predictions_json = os.path.join(selected_folder, "predictions.json")
            if os.path.exists(predictions_json):
                with open(predictions_json, 'r') as f:
                    st.session_state.predictions_data = json.load(f)
                    st.session_state.show_predictions = True
            else:
                st.session_state.predictions_data = None
                st.session_state.show_predictions = False
            
            st.rerun()
        else:
            st.warning("No folder selected")
    
    if st.button("Reload Folder"):
        if st.session_state.current_folder:
            st.session_state.image_files = load_folder_images(st.session_state.current_folder)
            # Reload predictions if available
            predictions_json = os.path.join(st.session_state.current_folder, "predictions.json")
            if os.path.exists(predictions_json):
                with open(predictions_json, 'r') as f:
                    st.session_state.predictions_data = json.load(f)
            st.rerun()
    
    st.markdown("---")
    
    # Destination folders
    st.header("🎯 Destination Folders")
    
    # Folder 1
    folder_1 = st.text_input(
        "Folder 1 (Button: 1)",
        value=st.session_state.folder_1 or "",
        help="Destination folder for key '1'",
        key="folder_1_input"
    )
    if folder_1 != st.session_state.folder_1:
        st.session_state.folder_1 = folder_1
    
    if st.button("Browse for Folder 1", use_container_width=True):
        selected = browse_folder()
        if selected:
            st.session_state.folder_1 = selected
            st.rerun()
    
    # Folder 2
    folder_2 = st.text_input(
        "Folder 2 (Button: 2)",
        value=st.session_state.folder_2 or "",
        help="Destination folder for key '2'",
        key="folder_2_input"
    )
    if folder_2 != st.session_state.folder_2:
        st.session_state.folder_2 = folder_2
    
    if st.button("Browse for Folder 2", use_container_width=True):
        selected = browse_folder()
        if selected:
            st.session_state.folder_2 = selected
            st.rerun()
    
    # Folder 3
    folder_3 = st.text_input(
        "Folder 3 (Button: 3)",
        value=st.session_state.folder_3 or "",
        help="Destination folder for key '3'",
        key="folder_3_input"
    )
    if folder_3 != st.session_state.folder_3:
        st.session_state.folder_3 = folder_3
    
    if st.button("Browse for Folder 3", use_container_width=True):
        selected = browse_folder()
        if selected:
            st.session_state.folder_3 = selected
            st.rerun()
    
    st.markdown("---")
    
    # AI Tools
    st.header("🤖 AI Tools")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Run SpeciesNet", use_container_width=True):
            if st.session_state.current_folder:
                run_speciesnet(st.session_state.current_folder)
                st.rerun()
            else:
                st.error("Please load a folder first")
    
    with col2:
        if st.button("Run MegaDetector", use_container_width=True):
            if st.session_state.current_folder:
                run_megadetector(st.session_state.current_folder)
                st.rerun()
            else:
                st.error("Please load a folder first")
    
    # Show predictions toggle
    if st.session_state.predictions_data:
        st.session_state.show_predictions = st.checkbox(
            "Show Predictions",
            value=st.session_state.show_predictions
        )
    
    st.markdown("---")
    
    # Logs
    with st.expander("📋 View Logs", expanded=False):
        if st.session_state.logs:
            for log in reversed(st.session_state.logs[-20:]):  # Show last 20 logs
                st.text(log)
        else:
            st.info("No logs yet")

# Main content area
if st.session_state.image_files:
    # Image counter and navigation
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⬅️ Prev"):
            if st.session_state.current_image_index > 0:
                st.session_state.current_image_index -= 1
                st.rerun()
    
    with col2:
        if st.button("➡️ Next"):
            if st.session_state.current_image_index < len(st.session_state.image_files) - 1:
                st.session_state.current_image_index += 1
                st.rerun()
    
    with col3:
        st.markdown(
            f"<h3 style='text-align: center;'>Image {st.session_state.current_image_index + 1} / {len(st.session_state.image_files)}</h3>",
            unsafe_allow_html=True
        )
    
    with col4:
        # Jump to image
        jump_to = st.number_input(
            "Jump to",
            min_value=1,
            max_value=len(st.session_state.image_files),
            value=st.session_state.current_image_index + 1,
            step=1,
            label_visibility="collapsed"
        )
        if jump_to - 1 != st.session_state.current_image_index:
            st.session_state.current_image_index = jump_to - 1
            st.rerun()
    
    with col5:
        pass
    
    # Display current image
    current_image_path = st.session_state.image_files[st.session_state.current_image_index]
    
    # Create two columns: image and info
    img_col, info_col = st.columns([3, 1])
    
    with img_col:
        try:
            image = Image.open(current_image_path)
            st.image(image, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading image: {str(e)}")
        
        # Copy buttons below image
        st.markdown("### 📤 Copy Image To:")
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        with btn_col1:
            if st.button(f"📁 Folder 1", use_container_width=True, key="copy1"):
                if st.session_state.folder_1:
                    copy_image_to_folder(current_image_path, st.session_state.folder_1)
                else:
                    st.error("Folder 1 not set")
        
        with btn_col2:
            if st.button(f"📁 Folder 2", use_container_width=True, key="copy2"):
                if st.session_state.folder_2:
                    copy_image_to_folder(current_image_path, st.session_state.folder_2)
                else:
                    st.error("Folder 2 not set")
        
        with btn_col3:
            if st.button(f"📁 Folder 3", use_container_width=True, key="copy3"):
                if st.session_state.folder_3:
                    copy_image_to_folder(current_image_path, st.session_state.folder_3)
                else:
                    st.error("Folder 3 not set")
    
    with info_col:
        st.subheader("📊 Image Info")
        st.write(f"**Filename:** {os.path.basename(current_image_path)}")
        
        try:
            image = Image.open(current_image_path)
            st.write(f"**Size:** {image.size[0]} x {image.size[1]}")
            st.write(f"**Format:** {image.format}")
        except:
            pass
        
        # Display predictions if available
        display_predictions_info()
    
    # Thumbnail gallery at bottom
    st.markdown("---")
    st.subheader("🖼️ Image Gallery")
    
    # Show thumbnails in rows
    images_per_row = 8
    num_images = len(st.session_state.image_files)
    
    # Calculate which thumbnails to show (around current image)
    start_idx = max(0, st.session_state.current_image_index - images_per_row // 2)
    end_idx = min(num_images, start_idx + images_per_row * 2)
    
    cols = st.columns(images_per_row)
    for idx in range(start_idx, end_idx):
        col_idx = (idx - start_idx) % images_per_row
        with cols[col_idx]:
            try:
                img_path = st.session_state.image_files[idx]
                img = Image.open(img_path)
                img.thumbnail((150, 150))
                
                # Highlight current image
                if idx == st.session_state.current_image_index:
                    st.markdown("**▶️ Current**")
                
                if st.button(f"", key=f"thumb_{idx}", use_container_width=True):
                    st.session_state.current_image_index = idx
                    st.rerun()
                
                st.image(img, use_container_width=True)
                st.caption(f"{idx + 1}")
            except:
                pass

else:
    # No images loaded
    st.info("👈 Please load a folder from the sidebar to get started")
    
    st.markdown("""
    ## How to Use:
    
    ### 1. Image Sorting
    1. Enter the path to your image folder in the sidebar
    2. Click "Load Folder" to load all images
    3. Define up to 3 destination folders
    4. Navigate through images using Previous/Next buttons
    5. Click the folder buttons to copy the current image
    
    ### 2. SpeciesNet Detection
    1. Load a folder containing wildlife images
    2. Click "Run SpeciesNet" to detect species
    3. A `predictions.json` file will be generated with species probabilities
    4. View detection results in the image info panel
    
    ### 3. MegaDetector Visualization
    1. After running SpeciesNet, click "Run MegaDetector"
    2. New images with bounding boxes will be generated
    3. Click "Reload Folder" to see the new visualizations
    
    ### 4. Navigation Tips
    - Use the thumbnail gallery at the bottom to quickly jump to images
    - Use the "Jump to" field to go to a specific image number
    - View logs in the sidebar to track operations
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>SpeciesNet Image Sorter - Streamlit Version</div>",
    unsafe_allow_html=True
)
