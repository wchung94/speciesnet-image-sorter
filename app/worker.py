from PyQt6.QtCore import QThread, pyqtSignal
import subprocess
import logging


class SpeciesnetWorker(QThread):
    """Worker thread to run subprocess commands without blocking the UI."""
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, cmd, folder, task_name="SpeciesNet"):
        super().__init__()
        self.cmd = cmd
        self.folder = folder
        self.task_name = task_name
        self.logger = logging.getLogger("ImageViewer")
        self.process = None
    
    def run(self):
        try:
            self.output_signal.emit(f"Starting {self.task_name} on folder: {self.folder}")
            self.logger.info(f"Starting {self.task_name} on folder: {self.folder}")
            
            # Run subprocess with output capture
            # start_new_session=True isolates the subprocess from parent's signal handlers
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                text=True,
                start_new_session=True,
                close_fds=True  # Close file descriptors in child process
            )
            
            # Read output in real-time
            while True:
                if not self.isRunning():
                    # Thread was requested to stop
                    break
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    self.output_signal.emit(output.strip())
                    self.logger.info(output.strip())
            
            # Wait for process to complete
            self.process.wait()
            
            return_code = self.process.returncode
            if return_code == 0:
                self.output_signal.emit(f"{self.task_name} completed successfully")
                self.logger.info(f"{self.task_name} completed successfully")
            else:
                error_msg = f"{self.task_name} exited with code {return_code}"
                self.error_signal.emit(error_msg)
                self.logger.error(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to run {self.task_name}: {str(e)}"
            self.error_signal.emit(error_msg)
            self.logger.error(error_msg)
        finally:
            # Ensure signals are emitted before thread exits
            self.finished_signal.emit()
            self.logger.info(f"{self.task_name} finished_signal emitted")
    
    def terminate_process(self):
        """Terminate the subprocess if it's still running."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                self.logger.error(f"Error terminating process: {e}")
