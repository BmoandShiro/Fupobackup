
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QCheckBox, QComboBox
from Weather_map import WeatherMap  # Import the interactive weather map

class WeatherDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌦️ Weather Dashboard")
        self.setGeometry(200, 100, 800, 600)
        self.init_ui()

    def init_ui(self):
        """Creates UI for the Weather Dashboard."""
        layout = QVBoxLayout()

        # **Weather Map (Embedded)**
        self.Weather_map = WeatherMap()
        layout.addWidget(self.Weather_map)

        # **Manual Location Entry**
        layout.addWidget(QLabel("🌍 Enter City:"))
        self.city_input = QLineEdit()
        layout.addWidget(self.city_input)

        # **Fetch Weather Button**
        self.fetch_weather_btn = QPushButton("🔍 Get Weather")
        self.fetch_weather_btn.clicked.connect(self.fetch_weather)
        layout.addWidget(self.fetch_weather_btn)

        # **Saved Locations**
        layout.addWidget(QLabel("📌 Saved Locations:"))
        self.saved_locations_list = QListWidget()
        layout.addWidget(self.saved_locations_list)

        # **Use Current Location Button**
        self.use_location_btn = QPushButton("📍 Use Current Location")
        self.use_location_btn.clicked.connect(self.fetch_current_weather)
        layout.addWidget(self.use_location_btn)

        # **Weather Alerts Toggle**
        self.alerts_toggle = QCheckBox("🔔 Enable NWS Alerts")
        layout.addWidget(self.alerts_toggle)

        # **Refresh Interval Dropdown**
        layout.addWidget(QLabel("🔄 Check Interval (seconds):"))
        self.interval_dropdown = QComboBox()
        self.interval_dropdown.addItems(["30", "60", "120"])
        layout.addWidget(self.interval_dropdown)

        # **Set Layout**
        self.setLayout(layout)

    def fetch_weather(self):
        """Fetches weather for entered city."""
        city = self.city_input.text()
        if city:
            print(f"Fetching weather for {city}...")  # Replace with API call

    def fetch_current_weather(self):
        """Fetches weather using current location."""
        print("Fetching weather for current location...")  # Replace with API call
