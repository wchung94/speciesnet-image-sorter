import logging
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt

class LogHandler(logging.Handler):
    """Custom logging handler that emits to a QTextEdit widget."""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
    
    def emit(self, record):
        """Emit a log record to the QTextEdit widget."""
        try:
            msg = self.format(record)
            self.text_edit.insertPlainText(msg + '\n')
            # Auto-scroll to bottom
            scrollbar = self.text_edit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception:
            self.handleError(record)