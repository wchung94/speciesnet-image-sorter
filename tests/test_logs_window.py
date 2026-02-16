"""Unit tests for logs_window module."""
import logging
import pytest
from PyQt6.QtWidgets import QApplication, QTextEdit
from app.logs_window import LogHandler


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestLogHandler:
    """Tests for LogHandler class."""
    
    def test_init(self, qapp):
        """Test LogHandler initialization."""
        text_edit = QTextEdit()
        handler = LogHandler(text_edit)
        
        assert handler.text_edit == text_edit
        assert hasattr(handler, 'log_message')
    
    def test_emit_appends_to_text_edit(self, qapp):
        """Test that emitting a log record appends to text edit."""
        text_edit = QTextEdit()
        handler = LogHandler(text_edit)
        
        # Create a logger and add handler
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Set formatter
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Log a message
        logger.info("Test message")
        
        # Process Qt events multiple times to ensure signal is processed
        for _ in range(10):
            QApplication.processEvents()
        
        # Check that message appears in text edit
        content = text_edit.toPlainText()
        assert "Test message" in content
        assert "INFO" in content
    
    def test_multiple_messages(self, qapp):
        """Test logging multiple messages."""
        text_edit = QTextEdit()
        handler = LogHandler(text_edit)
        
        logger = logging.getLogger("test_logger_multi")
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        # Log multiple messages
        logger.info("Message 1")
        logger.warning("Message 2")
        logger.error("Message 3")
        
        # Process Qt events
        QApplication.processEvents()
        
        content = text_edit.toPlainText()
        assert "Message 1" in content
        assert "Message 2" in content
        assert "Message 3" in content
    
    def test_auto_scroll(self, qapp):
        """Test that text edit auto-scrolls to bottom."""
        text_edit = QTextEdit()
        handler = LogHandler(text_edit)
        
        logger = logging.getLogger("test_logger_scroll")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Log many messages to trigger scrolling
        for i in range(50):
            logger.info(f"Message {i}")
        
        # Process Qt events
        QApplication.processEvents()
        
        # Check that scrollbar is at bottom
        scrollbar = text_edit.verticalScrollBar()
        # Should be at or near maximum
        assert scrollbar.value() >= scrollbar.maximum() - 10
