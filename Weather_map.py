import os
import json
import requests
import time  # Added for API rate-limiting prevention
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl  
from PyQt6.QtWebEngineCore import QWebEngineSettings
from weather_api import WeatherAPI
from flask import Flask, jsonify
import concurrent.futures  # Add for parallel requests

# Initialize Flask app
app = Flask(__name__)

class WeatherMap(QWidget):
    def __init__(self):
        super().__init__()
        self.map_loaded = False  # Track if map is loaded
        self.weather_api = WeatherAPI()
        self.latitude, self.longitude, self.location = self.weather_api.get_current_location()  # Get user's location
        self.current_zoom = 8 
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

        # Button to update heatmap overlay separately
        self.update_heatmap_button = QPushButton("Update Heatmap Overlay")
        self.update_heatmap_button.setEnabled(False)  # Disabled until map loads
        self.update_heatmap_button.clicked.connect(self.update_heatmap_overlay)  # Separate function
        self.layout.addWidget(self.update_heatmap_button)

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

            # Enable weather and heatmap update buttons
            self.update_weather_button.setEnabled(True)
            self.update_heatmap_button.setEnabled(True)
        else:
            print("🔄 Map already loaded.")

    def update_weather_overlay(self):
        """Fetches Open-Meteo weather data for the user's location only."""
        print(f"🟡 Fetching current weather data for coordinates: {self.latitude}, {self.longitude}")

        api_url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current_weather=true&timezone=auto"

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            weather_data = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "temp": data.get("current_weather", {}).get("temperature", "N/A"),
                "wind_speed": data.get("current_weather", {}).get("windspeed", "N/A"),
                "cloud_cover": data.get("hourly", {}).get("cloudcover", [None])[0]
            }

            # Save weather data as JSON
            templates_dir = os.path.abspath("templates")
            os.makedirs(templates_dir, exist_ok=True)  # Ensure directory exists
            weather_data_path = os.path.join(templates_dir, "weather_data.json")

            with open(weather_data_path, "w") as file:
                json.dump(weather_data, file)

            print(f"✅ Weather data saved at: {weather_data_path}")

            # Trigger JavaScript update
            if hasattr(self, "browser"):
                self.browser.page().runJavaScript("updateWeatherOverlay();")

        except requests.exceptions.RequestException as req_err:
            print(f"❌ ERROR fetching weather: {req_err}")

    def update_heatmap_overlay(self):
        """Fetches Open-Meteo weather data based on zoom level and updates the heatmap."""
        print(f"🟡 Fetching heatmap data for center coordinates: {self.latitude}, {self.longitude} (Zoom: {self.current_zoom})")

        # Adjust spacing based on zoom level
        if self.current_zoom > 10:   # High detail (zoomed in)
            spacing = 0.1
        elif self.current_zoom > 6:  # Medium detail
            spacing = 0.3
        else:                        # Low detail (zoomed out)
            spacing = 0.6

        lat_min, lat_max = self.latitude - 2, self.latitude + 2
        lon_min, lon_max = self.longitude - 2, self.longitude + 2

        print(f"📍 Heatmap bounding box: Lat({lat_min} to {lat_max}), Lon({lon_min} to {lon_max})")

        lat_points = [round(lat_min + i * spacing, 2) for i in range(int((lat_max - lat_min) / spacing) + 1)]
        lon_points = [round(lon_min + i * spacing, 2) for i in range(int((lon_max - lon_min) / spacing) + 1)]

        weather_data = []

        def fetch_weather(lat, lon):
            """Fetches weather data for a specific location."""
            api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
            try:
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()

                temp_celsius = data.get("current_weather", {}).get("temperature", None)
                if temp_celsius is not None:
                    temp_fahrenheit = round((temp_celsius * 9/5) + 32, 2)  # ✅ Convert °C → °F
                    print(f"✅ Data: {lat}, {lon} -> Temp: {temp_fahrenheit}°F")
                    return {"latitude": lat, "longitude": lon, "intensity": temp_fahrenheit}  # ✅ Store in °F
            except requests.exceptions.RequestException as req_err:
                print(f"❌ ERROR fetching weather at ({lat}, {lon}): {req_err}")
            return None

        # Fetch data in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_weather, lat, lon): (lat, lon) for lat in lat_points for lon in lon_points}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    weather_data.append(result)

        if not weather_data:
            print("⚠️ No weather data collected! Heatmap file will be empty.")

        # Save heatmap data
        templates_dir = os.path.abspath("templates")
        os.makedirs(templates_dir, exist_ok=True)
        heatmap_data_path = os.path.join(templates_dir, "heatmap_data.json")

        try:
            with open(heatmap_data_path, "w") as file:
                json.dump(weather_data, file)
            print(f"✅ Heatmap data saved successfully at: {heatmap_data_path}")

            # ✅ Ensure the browser refreshes the heatmap after saving new data
            if hasattr(self, "browser"):
                print("🔄 Running updateHeatmapOverlay() in JavaScript")
                self.browser.page().runJavaScript("updateHeatmapOverlay();")  # Refresh heatmap

        except Exception as e:
            print(f"❌ ERROR writing heatmap_data.json: {e}")


# 🔹 Flask Route to Update Zoom Level
@app.route('/set_zoom/<int:zoom>', methods=['GET'])
def set_zoom(zoom):
    """Updates zoom level dynamically based on user input from JavaScript."""
    global weather_map
    weather_map.current_zoom = zoom
    print(f"🔄 Updated zoom level to: {zoom}")
    return jsonify({"status": "success", "zoom": zoom})

# Start Flask in a Background Thread
def run_flask():
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

# Start Flask when the application runs
if __name__ == "__main__":
    weather_map = WeatherMap()
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()