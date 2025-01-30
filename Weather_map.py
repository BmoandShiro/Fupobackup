import os
import json
import requests
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl  
from PyQt6.QtWebEngineCore import QWebEngineSettings

class WeatherMap(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Sets up the PyQt WebEngineView to display an interactive map."""
        layout = QVBoxLayout()
        self.browser = QWebEngineView()

        # ✅ Enable local file and remote content access to prevent CORS issues
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

        self.load_map()
        layout.addWidget(self.browser)
        self.setLayout(layout)

    def load_map(self):
        """Loads the embedded map.html file."""
        map_path = os.path.abspath("templates/map.html")

        if not os.path.exists(map_path):
            print(f"⚠️ ERROR: Map file not found at {map_path}")
        else:
            print(f"✅ Map file exists: {map_path}")

        self.browser.setUrl(QUrl.fromLocalFile(map_path))

    def update_weather_overlay(self):
        """Fetches Open-Meteo weather data and updates the map overlay dynamically."""
        api_url = "https://api.open-meteo.com/v1/forecast?latitude=42.3314&longitude=-83.0458&current_weather=true&hourly=temperature_2m,cloudcover,precipitation&timezone=auto"
        response = requests.get(api_url)
        
        if response.status_code != 200:
            print(f"❌ API request failed with status code {response.status_code}")
            return
        
        data = response.json()
        weather_overlay = {}
        
        if "current_weather" in data:
            temp = data["current_weather"]["temperature"]
            wind_speed = data["current_weather"]["windspeed"]
            cloud_cover = data["hourly"]["cloudcover"][0]

            weather_overlay = {
                "temp": temp,
                "wind_speed": wind_speed,
                "cloud_cover": cloud_cover,
                "latitude": 42.3314,
                "longitude": -83.0458
            }

        # ✅ Ensure the templates folder exists
        templates_dir = os.path.abspath("templates")
        os.makedirs(templates_dir, exist_ok=True)

        # ✅ Save weather overlay to JSON
        weather_data_path = os.path.join(templates_dir, "weather_data.json")
        with open(weather_data_path, "w") as file:
            json.dump(weather_overlay, file, indent=4)
        
        print(f"✅ Weather data saved at {weather_data_path}")

        # ✅ Reload the map dynamically
        self.browser.page().runJavaScript("location.reload();")
