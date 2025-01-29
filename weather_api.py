import requests

def degrees_to_direction(degrees):
    """Convert wind direction in degrees to NESW compass points."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(degrees / 45) % 8
    return directions[index]

class WeatherAPI:
    def __init__(self):
        pass  # No API key needed for Open-Meteo

    def get_coordinates(self, city):
        """Convert city name to latitude & longitude using OpenStreetMap's Nominatim API."""
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={city}&limit=1"
        headers = {"User-Agent": "FupoAssistant/1.0 (contact: your-email@example.com)"}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Geocoding API Error {response.status_code}: {response.text}")
                return None, None, None

            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                city_name = data[0].get("name", city)
                state = data[0].get("state", "")
                country = data[0].get("country", "")

                formatted_location = f"{city_name}, {state}, {country}".replace(" ,", "").strip(", ")
                return lat, lon, formatted_location
            else:
                print(f"Could not retrieve coordinates for: {city}")
                return None, None, None
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None, None, None

    def get_weather(self, city="auto"):
        """Fetches weather data from Open-Meteo."""
        if city.lower() == "auto":
            return "Please specify a city."

        lat, lon, location = self.get_coordinates(city)
        if lat is None or lon is None:
            return f"Could not get coordinates for {city}. Try a more specific location."

        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&current_weather=true&timezone=auto&daily=sunrise,sunset")

        try:
            response = requests.get(url).json()

            if "current_weather" in response:
                weather = response["current_weather"]
                temp_c = weather["temperature"]
                temp_f = round((temp_c * 9/5) + 32, 1)  # Convert to Fahrenheit
                wind_speed = weather["windspeed"]
                wind_dir = degrees_to_direction(weather["winddirection"])  # Convert to NESW

                # Get sunrise & sunset times
                sunrise = response.get("daily", {}).get("sunrise", ["N/A"])[0][-5:]  # HH:MM format
                sunset = response.get("daily", {}).get("sunset", ["N/A"])[0][-5:]  # HH:MM format

                return (
                    f"🌍 **Weather in {location}:**\n"
                    f"🌡️ Temperature: {temp_c}°C ({temp_f}°F)\n"
                    f"💨 Wind Speed: {wind_speed} km/h\n"
                    f"🧭 Wind Direction: {wind_dir}\n"
                    f"🌅 Sunrise: {sunrise} | 🌇 Sunset: {sunset}"
                )
            else:
                return "Weather data not available."
        except Exception as e:
            return f"Error fetching weather data: {e}"
