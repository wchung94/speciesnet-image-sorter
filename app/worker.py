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
    
    def run(self):
        try:
            self.output_signal.emit(f"Starting {self.task_name} on folder: {self.folder}")
            self.logger.info(f"Starting {self.task_name} on folder: {self.folder}")
            
            # Run subprocess with output capture
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                text=True
            )
            
            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.output_signal.emit(output.strip())
                    self.logger.info(output.strip())
            
            # Wait for process to complete
            process.wait()
            
            return_code = process.returncode
            if return_code == 0:
                self.output_signal.emit(f"{self.task_name} completed successfully")
                self.logger.info(f"{self.task_name} completed successfully")
            else:
                error_msg = f"{self.task_name} exited with code {return_code}"
                self.error_signal.emit(error_msg)
                self.logger.error(error_msg)
            
            self.finished_signal.emit()
            self.logger.info(f"{self.task_name} finshed_signal emitter")
            
        except Exception as e:
            error_msg = f"Failed to run {self.task_name}: {str(e)}"
            self.error_signal.emit(error_msg)
            self.logger.error(error_msg)
            self.finished_signal.emit()
