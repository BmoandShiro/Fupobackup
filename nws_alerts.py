
import requests
import json
import threading
import time

class NWSWeatherMonitor:
    def __init__(self, settings):
        self.api_url = "https://api.weather.gov/alerts/active"
        self.monitoring_enabled = settings.get("monitor_weather_statements", False)
        self.locations = settings.get("weather_monitor_locations", [])
        self.check_interval = settings.get("weather_check_interval", 60)
        self.last_alerts = {}  # Store last alerts to prevent duplicates

    def fetch_weather_statements(self):
        """Fetches active weather alerts for monitored locations."""
        if not self.monitoring_enabled or not self.locations:
            return
        
        headers = {"User-Agent": "FupoAssistant/1.0 (contact: your-email@example.com)"}
        response = requests.get(self.api_url, headers=headers)

        if response.status_code != 200:
            print(f"❌ NWS API Error {response.status_code}: {response.text}")
            return

        data = response.json()
        alerts = data.get("features", [])

        new_alerts = []
        for alert in alerts:
            properties = alert["properties"]
            event = properties.get("event", "Unknown Alert")
            headline = properties.get("headline", "No headline")
            description = properties.get("description", "No description available.")
            affected_areas = properties.get("areaDesc", "")

            # Check if any monitored locations match the affected area
            if any(location.lower() in affected_areas.lower() for location in self.locations):
                if headline not in self.last_alerts:  # Avoid duplicates
                    new_alerts.append(f"🚨 {event}: {headline}\n📍 Affected: {affected_areas}\n📝 {description}\n")
                    self.last_alerts[headline] = time.time()

        # Remove old alerts (clear alerts older than 1 hour)
        self.last_alerts = {k: v for k, v in self.last_alerts.items() if time.time() - v < 3600}

        if new_alerts:
            for alert in new_alerts:
                print(alert)  # Display in terminal/UI
                self.speak_alert(alert)  # Optionally read aloud

    def speak_alert(self, message):
        """Speaks out the alert if the setting is enabled."""
        print(f"🔊 Speaking: {message}")  # Replace with actual TTS method

    def start_monitoring(self):
        """Runs a loop that fetches weather alerts at set intervals."""
        def monitor_loop():
            while self.monitoring_enabled:
                self.fetch_weather_statements()
                time.sleep(self.check_interval)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
