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

    def update_weather_overlay():
        """Fetches Open-Meteo weather data and updates the map overlay dynamically."""
        api_url = "https://api.open-meteo.com/v1/forecast?latitude=42.3314&longitude=-83.0458&current_weather=true&hourly=temperature_2m,cloudcover,precipitation&timezone=auto"

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
                "latitude": 42.3314,
                "longitude": -83.0458
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

        except requests.exceptions.RequestException as req_err:
            print(f"❌ ERROR: Failed to fetch weather data - {req_err}")
        except json.JSONDecodeError as json_err:
            print(f"❌ ERROR: JSON decoding failed - {json_err}")
        except Exception as e:
            print(f"❌ Unexpected ERROR: {e}")

    # Run the function manually to create the JSON
    update_weather_overlay()