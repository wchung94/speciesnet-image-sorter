import logging
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt, QObject, pyqtSignal

class LogHandler(logging.Handler, QObject):
    """Custom logging handler that emits to a QTextEdit widget in a thread-safe manner."""
    log_message = pyqtSignal(str)
    
    def __init__(self, text_edit):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.text_edit = text_edit
        # Connect signal to slot in the main GUI thread
        self.log_message.connect(self._append_message, Qt.ConnectionType.QueuedConnection)
    
    def emit(self, record):
        """Emit a log record to the QTextEdit widget via signal (thread-safe)."""
        try:
            msg = self.format(record)
            # Use signal to ensure GUI update happens in main thread
            self.log_message.emit(msg)
        except Exception:
            self.handleError(record)
    
    def _append_message(self, msg):
        """Append message to text edit (called in main GUI thread)."""
        try:
            self.text_edit.insertPlainText(msg + '\n')
            # Auto-scroll to bottom
            scrollbar = self.text_edit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except RuntimeError:
            # Widget was deleted
            pass