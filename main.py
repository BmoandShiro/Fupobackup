# Import statements
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QCoreApplication
from desktop_assistant import DesktopAssistant
import sys

# The main application block
if __name__ == "__main__":
    # ✅ Ensure application name is set before initializing QApplication
    QCoreApplication.setApplicationName("Desktop Assistant")
    QCoreApplication.setOrganizationName("YourOrganization")  # Optional but recommended

    app = QApplication(sys.argv)  # ✅ Pass sys.argv properly
    window = QMainWindow()  # Create the main window
    window.setWindowTitle("Desktop Assistant")

    desktop_assistant = DesktopAssistant(window)
    window.setCentralWidget(desktop_assistant)  # Set DesktopAssistant as the central widget

    window.show()  # Show the main window
    sys.exit(app.exec())  # Ensure clean exit
