"""Entry point for the Streamlit web app (referenced by run.sh)."""

import subprocess
import sys
import os

if __name__ == "__main__":
    app_path = os.path.join(os.path.dirname(__file__), "app", "streamlit_app.py")
    sys.exit(
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path]).returncode
    )
