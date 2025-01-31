
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QCheckBox, QComboBox, QDialog, QMessageBox, QSlider, QLabel
from Weather_map import WeatherMap  # Import the interactive weather map
from weather_api import WeatherAPI  # Ensure WeatherAPI is imported

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
        layout.addWidget(QLabel("🌍 Enter City State:"))
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
        
        # **Heatmap Settings Button**
        self.heatmap_settings_btn = QPushButton("⚙ Heatmap Settings")
        self.heatmap_settings_btn.clicked.connect(self.open_heatmap_settings)
        layout.addWidget(self.heatmap_settings_btn)


        # **Heatmap Toggle Button**
        self.toggle_heatmap_btn = QPushButton("🌡️ Toggle Heatmap")
        self.toggle_heatmap_btn.setCheckable(True)  # Enables toggle functionality
        self.toggle_heatmap_btn.setChecked(True)  # Default: ON
        self.toggle_heatmap_btn.clicked.connect(self.toggle_heatmap)
        layout.addWidget(self.toggle_heatmap_btn)


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
        """Fetches weather for the entered city and updates the map."""
        city = self.city_input.text().strip()

        if city:
            print(f"🔍 Fetching weather for {city}...")
            weather_api = WeatherAPI()
            latitude, longitude, location = weather_api.get_coordinates(city)
    
            if latitude and longitude:
                # Update the weather map's location
                self.Weather_map.latitude = latitude
                self.Weather_map.longitude = longitude
                self.Weather_map.location = location

                print(f"📍 Updated Coordinates: {latitude}, {longitude} ({location})")
        
                # Trigger weather update **after** coordinates are updated
                self.Weather_map.update_weather_overlay()
                self.Weather_map.update_heatmap_overlay()  # Ensure heatmap updates too
            else:
                print(f"⚠️ Could not find coordinates for {city}")


    def fetch_current_weather(self):
        """Fetches weather using current location."""
        print("Fetching weather for current location...")  # Replace with API call

    def toggle_heatmap(self):
        """Enable or disable heatmap visibility on the map."""
        is_enabled = self.toggle_heatmap_btn.isChecked()
        js_command = "showHeatmap(true);" if is_enabled else "showHeatmap(false);"
    
        if hasattr(self.Weather_map, "browser"):
            self.Weather_map.browser.page().runJavaScript(js_command)

    def open_heatmap_settings(self):
        """Opens a settings dialog for adjusting the heatmap parameters."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Heatmap Settings")
        dialog.setGeometry(300, 200, 300, 250)

        layout = QVBoxLayout()

        # Intensity Slider
        layout.addWidget(QLabel("🔥 Heatmap Intensity"))
        intensity_slider = QSlider()
        intensity_slider.setMinimum(1)
        intensity_slider.setMaximum(10)
        intensity_slider.setValue(5)
        layout.addWidget(intensity_slider)

        # Radius Slider
        layout.addWidget(QLabel("🎯 Point Radius"))
        radius_slider = QSlider()
        radius_slider.setMinimum(5)
        radius_slider.setMaximum(50)
        radius_slider.setValue(20)
        layout.addWidget(radius_slider)

        # Blur Slider
        layout.addWidget(QLabel("🌫️ Blur Level"))
        blur_slider = QSlider()
        blur_slider.setMinimum(5)
        blur_slider.setMaximum(50)
        blur_slider.setValue(15)
        layout.addWidget(blur_slider)

        # Apply Button
        apply_btn = QPushButton("Apply Settings")
        apply_btn.clicked.connect(lambda: self.apply_heatmap_settings(intensity_slider.value(), radius_slider.value(), blur_slider.value()))
        layout.addWidget(apply_btn)

        dialog.setLayout(layout)
        dialog.exec()
        
    def apply_heatmap_settings(self, intensity, radius, blur):
        """Applies user-defined heatmap settings dynamically."""
        js_command = f"updateHeatmapSettings({intensity}, {radius}, {blur});"
    
        if hasattr(self.Weather_map, "browser"):
            self.Weather_map.browser.page().runJavaScript(js_command)
