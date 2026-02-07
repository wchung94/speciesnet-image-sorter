"""Pytest configuration and fixtures."""
import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    """Create a single QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app here as it may be needed by other tests
