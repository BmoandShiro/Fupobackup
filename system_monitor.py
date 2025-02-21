# system_monitor.py
import psutil
from PyQt6.QtCore import QThread, pyqtSignal
import time

class SystemMonitor(QThread):
    stats_updated = pyqtSignal(float, float, float, float, float)  # CPU %, RAM %, RAM used, RAM total, Disk %

    def __init__(self, interval=5000):  # Default 5 seconds in milliseconds
        super().__init__()
        self.running = True
        self.enabled = False
        self.interval = interval  # Update interval in milliseconds
        self.cpu_history = []  # Store history for charting
        self.ram_history = []
        self.disk_history = []
        self.max_points = 100  # Limit history to last 100 points for performance

    def run(self):
        while self.running:
            if self.enabled:
                cpu_percent = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Add to history (limit size)
                self.cpu_history.append(cpu_percent)
                self.ram_history.append(ram.percent)
                self.disk_history.append(disk.percent)
                if len(self.cpu_history) > self.max_points:
                    self.cpu_history.pop(0)
                    self.ram_history.pop(0)
                    self.disk_history.pop(0)
                
                self.stats_updated.emit(cpu_percent, ram.percent, ram.used / 1024**3, ram.total / 1024**3, disk.percent)
            time.sleep(self.interval / 1000)  # Convert to seconds

    def stop(self):
        self.running = False
        self.wait()

    def set_enabled(self, enabled):
        self.enabled = enabled

    def set_interval(self, interval_ms):
        """Update the refresh interval (in milliseconds)."""
        self.interval = max(1000, interval_ms)  # Minimum 1 second to prevent overload