import os
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtGui import QIcon, QPixmap
from .thumbnail_creator import create_thumbnail
from PyQt6.QtCore import Qt


def load_image(file_path, image_label):
    """Load and display the image in the label."""
    image = QPixmap(file_path)
    scaled_image = image.scaled(
        image_label.size(),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    image_label.setPixmap(scaled_image)


def load_folder_images(folder_path, file_list):
    """Load all image files from the specified folder."""
    image_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
    file_list.clear()
    image_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in image_extensions
    ]
    image_files.sort()

    for image_path in image_files:
        item = QListWidgetItem()
        item.setIcon(QIcon(create_thumbnail(image_path)))
        item.setText(os.path.basename(image_path))
        item.setData(Qt.ItemDataRole.UserRole, image_path)
        file_list.addItem(item)

    return image_files
