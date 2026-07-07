import shutil
import os


def copy_current_image_to_new_folder(new_folder_path, image_files, current_image_index):
    """Copy the current image to the selected new folder."""
    if new_folder_path and image_files:
        current_image_file = image_files[current_image_index]
        destination = os.path.join(
            new_folder_path, os.path.basename(current_image_file)
        )
        shutil.copy(current_image_file, destination)
        print(f"Copied {current_image_file} to {destination}")
