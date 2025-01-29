import requests

class WeatherAPI:
    def __init__(self):
        pass  # No API key needed for Open-Meteo

    def get_coordinates(self, city):
        """Convert city name to latitude & longitude using OpenStreetMap's Nominatim API."""
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={city}&limit=1"
        headers = {
            "User-Agent": "FupoAssistant/1.0 (contact: your-email@example.com)"
        }  # OpenStreetMap requires a User-Agent

        try:
            response = requests.get(url, headers=headers)
        
            # Check if the response is empty or invalid
            if response.status_code != 200:
                print(f"Geocoding API Error {response.status_code}: {response.text}")
                return None, None

            data = response.json()

            if data and isinstance(data, list) and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return lat, lon
            else:
                print(f"Could not retrieve coordinates for: {city}")
                return None, None
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None, None



    def get_weather(self, city="auto"):
        """Fetches weather data from Open-Meteo."""
        if city.lower() == "auto":
            return "Please specify a city."

        lat, lon = self.get_coordinates(city)
        if lat is None or lon is None:
            return f"Could not find coordinates for {city}."

        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

        try:
            response = requests.get(url).json()
            if "current_weather" in response:
                weather = response["current_weather"]
                temp = weather["temperature"]
                wind_speed = weather["windspeed"]
                return f"The weather in {city} is {temp}°C with wind speeds of {wind_speed} km/h."
            else:
                return "Weather data not available."
        except Exception as e:
            return f"Error fetching weather data: {e}"
