# SpeciesNetImageSorter
SpeciesNet and Megadetector application to easily identify species on wildlife photos and sort them in folders.

This application is available in two versions:
- **Desktop Application**: PyQt6-based GUI with keyboard shortcuts for fast sorting
- **Web Application**: Streamlit-based web interface (📦 **now deployable to Databricks Apps!**)

## Quick Start

### Desktop Version
```bash
# Install dependencies
pip install -e ".[desktop]"

# Run the application
python main.py
```

### Web Version (Local)

**Using uv (recommended):**
```bash
# Dependencies are automatically managed by uv
uv run streamlit run streamlit_main.py
```

**Using pip:**
```bash
# Install dependencies
pip install -e ".[streamlit]"

# Run the application
streamlit run streamlit_main.py
```

### Deploy to Databricks Apps
See [Databricks Deployment](#databricks-deployment) section below.

## Requirements
- For Desktop: Windows/Mac/Linux Computer with 4 GB RAM minimum
- For Web/Databricks: Python 3.10+ with 4 GB RAM (Depends on number of images)
- CPU that can handle AI inference workloads
- Databricks workspace (for Databricks Apps deployment)

---

## Databricks Deployment

The application is now fully compatible with **Databricks Apps**! Deploy your image sorter to a Databricks workspace in minutes.

### Prerequisites
- Databricks workspace with admin access
- Databricks CLI installed and configured
- Git repository with this code

### Step 1: Prepare Your Code
Ensure your repository is cloned in Databricks:
```bash
# In Databricks terminal or notebook
git clone <your-repo-url>
cd SimpleImageSorter
```

### Step 2: Deploy Using Databricks CLI
```bash
# Navigate to your repo
cd /path/to/SimpleImageSorter

# Deploy the app
databricks apps create --config-path databricks.yml
```

### Step 3: Access Your App
Once deployed, access your app through:
- Databricks workspace UI → Apps section
- Direct URL: `https://<your-workspace>.cloud.databricks.com/apps/<app-id>`

### Configuration Options

The `databricks.yml` file controls deployment settings:

```yaml
name: "simple-image-sorter"          # App name
title: "Simple Image Sorter"          # Display title
description: "..."                    # App description
source:
  path: streamlit_main.py             # Entry point
```

### Using with Databricks File System

To work with files in Databricks, modify the folder paths to use `/Volumes/`:

**Example:**
```
/Volumes/my-catalog/my-schema/wildlife-photos/
```

Or use Unity Catalog paths in the web UI.

### Troubleshooting

**Issue: Module not found errors**
- Ensure all dependencies are listed in `pyproject.toml`
- Run: `pip install -e ".[streamlit]"` locally first to test

**Issue: Files not accessible**
- Check file paths are absolute paths
- Use `/Volumes/` paths for Databricks File System access
- Verify read/write permissions on folders

**Issue: App timeout**
- For large image folders (1000+ images), consider chunking the data
- Optimize thumbnail generation

### Advanced: Custom Compute

For ML workloads, you can use specific Databricks clusters:

```yaml
resources:
  compute: ["databricks.workspace.compute"]
```

Upgrade to a cluster with GPU if available for faster inference.

---

## File Structure

```
./SimpleImageSorter/
    ├── main.py                           # Desktop app entry point (PyQt6)
    ├── streamlit_main.py                 # Web app entry point (Streamlit)
    ├── databricks.yml                    # Databricks deployment config
    ├── pyproject.toml                    # Dependencies
    ├── README.md
    └── app/
        ├── image_viewer.py               # Main UI (PyQt6)
        ├── streamlit_app.py              # Web UI (Streamlit)
        ├── image_loader.py               # Image loading utilities
        ├── file_operations.py            # File operations
        ├── thumbnail_creator.py          # Thumbnail generation
        ├── speciesnet_buttonwidget.py    # SpeciesNet integration
        └── megadetector_buttonwidget.py  # MegaDetector integration
```

---

## Desktop App Usage

### Sorting Images
1. Launch the application
2. Select folder via "File → Open Folder"
3. Configure destination folders (Key 1, 2, 3)
4. Navigate with arrow keys (Up/Down/Left/Right)
5. Press 1, 2, or 3 to copy image to destination folder

### SpeciesNet Detection
1. Select folder with images
2. Click "Run SpeciesNet"
3. Results saved to `predictions.json`

### MegaDetector Bounding Boxes
1. After running SpeciesNet
2. Click "Run Megadetector"
3. Generated images with bounding boxes appear in folder

---

## Web App Usage (Streamlit)

### Image Sorting
1. Enter source folder path in sidebar
2. Configure destination folder paths
3. Use "Previous" and "Next" buttons to navigate
4. Click "Copy to Folder X" buttons to sort images

### AI Features
1. Click "Run SpeciesNet" to analyze images
2. View prediction results in sidebar
3. Click "Run MegaDetector" for bounding boxes

### Keyboard Navigation (Desktop Only)
- Arrow keys: Navigate images
- Numbers 1-3: Copy to destination folders

---

## Development

### Setup Development Environment
```bash
# Clone repo
git clone <repo-url>
cd SimpleImageSorter

# Install with dev dependencies
pip install -e ".[dev,desktop,streamlit]"

# Run tests
pytest

# Run desktop app
python main.py

# Run web app
streamlit run streamlit_main.py
```

### Contributing
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and test locally
3. Submit pull request

---


