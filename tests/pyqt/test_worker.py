"""Unit tests for worker module."""

import sys
import time
import pytest
from PyQt6.QtWidgets import QApplication
from app.worker import SpeciesnetWorker


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestSpeciesnetWorker:
    """Tests for SpeciesnetWorker class."""

    def test_init(self, qapp):
        """Test SpeciesnetWorker initialization."""
        cmd = [sys.executable, "-c", "print('test')"]
        folder = "/test/folder"

        worker = SpeciesnetWorker(cmd, folder)

        assert worker.cmd == cmd
        assert worker.folder == folder
        assert worker.task_name == "SpeciesNet"
        assert worker.process is None

    def test_init_custom_task_name(self, qapp):
        """Test initialization with custom task name."""
        cmd = [sys.executable, "-c", "print('test')"]
        folder = "/test/folder"

        worker = SpeciesnetWorker(cmd, folder, task_name="CustomTask")

        assert worker.task_name == "CustomTask"

    def test_simple_command_execution(self, qapp):
        """Test running a simple command."""
        cmd = [sys.executable, "-c", "print('Hello World')"]
        folder = "/test/folder"

        worker = SpeciesnetWorker(cmd, folder)

        # Track signals
        output_messages = []
        error_messages = []
        finished_called = []

        worker.output_signal.connect(lambda msg: output_messages.append(msg))
        worker.error_signal.connect(lambda msg: error_messages.append(msg))
        worker.finished_signal.connect(lambda: finished_called.append(True))

        worker.start()

        # Wait for worker to finish (with timeout)
        worker.wait(5000)

        # Process any pending events
        QApplication.processEvents()

        # Verify results
        assert len(finished_called) > 0, "Finished signal should have been emitted"
        assert any(
            "Hello World" in msg for msg in output_messages
        ), f"Expected 'Hello World' in output messages: {output_messages}"

    def test_command_with_error(self, qapp):
        """Test running a command that fails."""
        # Command that exits with error code
        cmd = [sys.executable, "-c", "import sys; sys.exit(1)"]
        folder = "/test/folder"

        worker = SpeciesnetWorker(cmd, folder)

        error_messages = []
        finished_called = []

        worker.error_signal.connect(lambda msg: error_messages.append(msg))
        worker.finished_signal.connect(lambda: finished_called.append(True))

        worker.start()
        worker.wait(5000)

        QApplication.processEvents()

        # Should have error message about exit code
        assert len(finished_called) > 0
        assert len(error_messages) > 0
        assert any("exited with code" in msg for msg in error_messages)

    def test_terminate_process(self, qapp):
        """Test terminating a running process."""
        # Command that runs for a while
        cmd = [sys.executable, "-c", "import time; time.sleep(10); print('done')"]
        folder = "/test/folder"

        worker = SpeciesnetWorker(cmd, folder)
        worker.start()

        # Give process time to start
        QApplication.processEvents()
        time.sleep(0.1)

        # Terminate the process
        worker.terminate_process()

        # Wait briefly
        worker.wait(2000)

        # Process should be terminated
        if worker.process:
            assert worker.process.poll() is not None, "Process should have terminated"

    def test_multiple_output_lines(self, qapp):
        """Test capturing multiple output lines."""
        cmd = [
            sys.executable,
            "-c",
            "print('Line 1'); print('Line 2'); print('Line 3')",
        ]
        folder = "/test/folder"

        worker = SpeciesnetWorker(cmd, folder)

        output_messages = []
        worker.output_signal.connect(lambda msg: output_messages.append(msg))

        worker.start()
        worker.wait(5000)

        QApplication.processEvents()

        # Should capture all three lines
        output_text = " ".join(output_messages)
        assert "Line 1" in output_text
        assert "Line 2" in output_text
        assert "Line 3" in output_text
