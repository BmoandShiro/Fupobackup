# Import statements
from PyQt6.QtWidgets import QApplication, QMainWindow
from desktop_assistant import DesktopAssistant

# The main application block
if __name__ == "__main__":
    app = QApplication([])  # Initialize the application
    window = QMainWindow()  # Create the main window
    window.setWindowTitle("Desktop Assistant")

    desktop_assistant = DesktopAssistant(window)
    window.setCentralWidget(desktop_assistant)  # Set DesktopAssistant as the central widget

    window.show()  # Show the main window
    app.exec()  # Start the application's event loop
