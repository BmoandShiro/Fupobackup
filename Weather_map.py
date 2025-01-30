
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl  # Import QUrl
import json
import requests

class WeatherMap(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.browser = QWebEngineView()
        self.load_map()
        layout.addWidget(self.browser)
        self.setLayout(layout)

    def init_ui(self):
        """Sets up the PyQt WebEngineView to display an interactive map."""
        layout = QVBoxLayout()
        self.browser = QWebEngineView()
        self.load_map()
        layout.addWidget(self.browser)
        self.setLayout(layout)

    def load_map(self):
        """Loads the embedded map.html file."""
        self.browser.setUrl(QUrl.fromLocalFile("C:/Users/BMO/Source/Repos/Fupobackup/templates/map.html"))
        
    def update_weather_overlay(self):
        """Fetches Open-Meteo weather data and updates the map overlay dynamically."""
        api_url = "https://api.open-meteo.com/v1/forecast?latitude=42.3314&longitude=-83.0458&current_weather=true&hourly=temperature_2m,cloudcover,precipitation&timezone=auto"
        response = requests.get(api_url)
        data = response.json()

        weather_overlay = []
        if "current_weather" in data:
            temp = data["current_weather"]["temperature"]
            wind_speed = data["current_weather"]["windspeed"]
            cloud_cover = data["hourly"]["cloudcover"][0]

            # Create JSON object for JavaScript to process
            weather_overlay = {
                "temp": temp,
                "wind_speed": wind_speed,
                "cloud_cover": cloud_cover,
                "latitude": 42.3314,
                "longitude": -83.0458
            }

        with open("templates/weather_data.json", "w") as file:
            json.dump(weather_overlay, file)
        
        # Reload the map to update overlays
        self.browser.reload()
