import os
import json
import requests
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl  
from PyQt6.QtWebEngineCore import QWebEngineSettings
from weather_api import WeatherAPI


class WeatherMap(QWidget):
    def __init__(self):
        super().__init__()
        self.map_loaded = False  # Track if map is loaded
        self.weather_api = WeatherAPI()
        self.latitude, self.longitude, self.location = self.weather_api.get_current_location()  # Get user's location
        self.init_ui()


    def init_ui(self):
        """Sets up the UI, but does NOT load the map or fetch weather data on start."""
        self.layout = QVBoxLayout()

        # Button to trigger map loading
        self.load_map_button = QPushButton("Load Weather Map")
        self.load_map_button.clicked.connect(self.load_map)
        self.layout.addWidget(self.load_map_button)

        # Button to update weather overlay (disabled until map loads)
        self.update_weather_button = QPushButton("Update Weather Overlay")
        self.update_weather_button.setEnabled(False)  # Starts disabled
        self.update_weather_button.clicked.connect(self.update_weather_overlay)
        self.layout.addWidget(self.update_weather_button)

        self.setLayout(self.layout)

    def load_map(self):
        """Loads the embedded map.html file when triggered."""
        if not self.map_loaded:
            map_path = os.path.abspath("templates/map.html")
            if not os.path.exists(map_path):
                print(f"⚠️ ERROR: Map file not found at {map_path}")
                return

            print(f"✅ Loading Map: {map_path}")
            self.browser = QWebEngineView()

            # Enable local content access to prevent CORS issues
            settings = self.browser.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

            self.browser.setUrl(QUrl.fromLocalFile(map_path))
            self.layout.addWidget(self.browser)
            self.map_loaded = True

            # Enable weather update button after map loads
            self.update_weather_button.setEnabled(True)
        else:
            print("🔄 Map already loaded.")

    def update_weather_overlay(self):
        """Fetches Open-Meteo weather data and updates the map overlay dynamically."""
        api_url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current_weather=true&hourly=temperature_2m,cloudcover,precipitation&timezone=auto"


        print("🟡 Fetching weather data from API...")

        try:
            response = requests.get(api_url)
            response.raise_for_status()  # Raises an error for HTTP failures
            data = response.json()
            print(f"✅ API Response: {json.dumps(data, indent=2)}")

            weather_overlay = {
                "temp": data.get("current_weather", {}).get("temperature", "N/A"),
                "wind_speed": data.get("current_weather", {}).get("windspeed", "N/A"),
                "cloud_cover": data.get("hourly", {}).get("cloudcover", [None])[0],
                "latitude": self.latitude,
                "longitude": self.longitude
            }

            print(f"🟢 Parsed Weather Data: {weather_overlay}")

            # Ensure templates directory exists
            templates_dir = os.path.abspath("templates")
            os.makedirs(templates_dir, exist_ok=True)

            # Save JSON file
            weather_data_path = os.path.join(templates_dir, "weather_data.json")
            with open(weather_data_path, "w") as file:
                json.dump(weather_overlay, file)

            print(f"✅ Weather data saved successfully at: {weather_data_path}")

            # Trigger JavaScript update only if the map is loaded
            if hasattr(self, "browser"):
                self.browser.page().runJavaScript("updateWeatherOverlay();")

        except requests.exceptions.RequestException as req_err:
            print(f"❌ ERROR: Failed to fetch weather data - {req_err}")
        except json.JSONDecodeError as json_err:
            print(f"❌ ERROR: JSON decoding failed - {json_err}")
        except Exception as e:
            print(f"❌ Unexpected ERROR: {e}")
