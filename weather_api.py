import requests
import datetime
import re

class WeatherAPI:
    def __init__(self):
        self.geo_api_url = "https://nominatim.openstreetmap.org/search"
        self.weather_api_url = "https://api.open-meteo.com/v1/forecast"

    def get_current_location(self):
        """Gets user's current location (latitude, longitude, city, state, country) using IP geolocation."""
        try:
            response = requests.get("https://ipapi.co/json/")
            if response.status_code == 200:
                data = response.json()
                lat = data.get("latitude")
                lon = data.get("longitude")
                city = data.get("city", "Unknown City")
                state = data.get("region", "")
                country = data.get("country_name", "Unknown Country")
                location = f"{city}, {state}, {country}".strip(", ")
                return lat, lon, location
            else:
                print(f"IP Geolocation Error {response.status_code}: {response.text}")
                return None, None, None
        except Exception as e:
            print(f"Error fetching location: {e}")
            return None, None, None

 

    def get_coordinates(self, city):
        """Convert city name to latitude & longitude using OpenStreetMap's Nominatim API."""
        url = f"{self.geo_api_url}?format=json&q={self.clean_location_query(city)}&limit=1"
        headers = {"User-Agent": "FupoAssistant/1.0 (contact: your-email@example.com)"}

        try:
            response = requests.get(url, headers=headers)
        
            if response.status_code != 200:
                print(f"⚠️ Geocoding API Error {response.status_code}: {response.text}")
                return None, None, f"Could not retrieve {city}"
        
            data = response.json()

            # 🔎 DEBUG: Print the full API response
            print(f"🔎 Geocoding API Response for '{city}': {data}")

            if isinstance(data, list) and len(data) > 0:
                location_info = data[0]

                lat = float(location_info.get("lat", 0))
                lon = float(location_info.get("lon", 0))

                # Handle missing fields
                city_name = location_info.get("name", city) or city
                state = location_info.get("state", "")
                country = location_info.get("country", "")

                # Format location properly
                formatted_location = f"{city_name}, {state}, {country}".replace(" ,", "").strip(", ")
                return lat, lon, formatted_location

            else:
                print(f"⚠️ No results found for: {city}")
                return None, None, f"Could not find {city}"

        except Exception as e:
            print(f"❌ Geocoding error: {e}")
            return None, None, f"Could not get coordinates for {city}"

    def clean_location_query(self, query):
        """Remove 'weather', 'temperature', and other non-location words from queries."""
        cleaned = re.sub(r"\b(weather|temperature|forecast|current)\b", "", query, flags=re.IGNORECASE).strip()
        print(f"🛠️ Cleaned query: '{cleaned}'")  # Debugging log
        return cleaned


    def get_weather(self, city="auto", spoken_request=""):
        """Fetches weather data from Open-Meteo, using either a city name or current location."""
    
        if city.lower() == "auto":
            lat, lon, location = self.get_current_location()
            if lat is None or lon is None:
                return "Could not detect your location. Try specifying a city.", "Could not detect your location."
        else:
            lat, lon, location = self.get_coordinates(city)

        if lat is None or lon is None:
            return f"Could not get coordinates for {city}. Try a more specific location.", f"Could not get coordinates for {city}."

        url = (f"{self.weather_api_url}?latitude={lat}&longitude={lon}"
               f"&current_weather=true&timezone=auto&daily=sunrise,sunset")

        try:
            response = requests.get(url).json()

            if "current_weather" in response:
                weather = response["current_weather"]
                temp_c = weather["temperature"]
                temp_f = round((temp_c * 9/5) + 32, 1)
                wind_speed_kmh = weather["windspeed"]
                wind_speed_mph = round(wind_speed_kmh * 0.621371, 1)
                wind_dir_degrees = weather["winddirection"]
                wind_dir = self.degrees_to_direction(wind_dir_degrees)

                sunrise = response.get("daily", {}).get("sunrise", ["N/A"])[0][-5:]
                sunset = response.get("daily", {}).get("sunset", ["N/A"])[0][-5:]

                sunrise_time = datetime.datetime.strptime(sunrise, "%H:%M").strftime("%I:%M %p")
                sunset_time = datetime.datetime.strptime(sunset, "%H:%M").strftime("%I:%M %p")

                # **SHOW ALL DATA IN TERMINAL**
                print(f"🌍 Weather in {location}")
                print(f"🌡️ Temperature: {temp_f}°F ({temp_c}°C)")
                print(f"💨 Wind Speed: {wind_speed_mph} mph")
                print(f"🧭 Wind Direction: {wind_dir}")
                print(f"🌅 Sunrise: {sunrise_time} | 🌇 Sunset: {sunset_time}")

                # **DISPLAY ALL DATA ON DASHBOARD**
                response_message = (
                    f"🌍 **Weather in {location}**\n"
                    f"🌡️ {temp_f}°F\n"
                    f"💨 {wind_speed_mph} mph\n"
                    f"🧭 Wind Direction: {wind_dir}\n"
                    f"🌅 Sunrise: {sunrise_time} | 🌇 Sunset: {sunset_time}"
                )

                # **SPOKEN RESPONSE - Only essential data**
                spoken_message = f"Weather in {location}: {temp_f}°F, {wind_speed_mph} mph."

                if "sunrise" in spoken_request.lower():
                    spoken_message += f" Sunrise is at {sunrise_time}."
                if "sunset" in spoken_request.lower():
                    spoken_message += f" Sunset is at {sunset_time}."
                if "wind direction" in spoken_request.lower():
                    spoken_message += f" Wind direction is {wind_dir}."

                return response_message, spoken_message  # ✅ Always return a tuple
            else:
                return "Weather data not available.", "Weather data not available."
        except Exception as e:
            return f"Error fetching weather data: {e}", f"Error fetching weather data."


    def degrees_to_direction(self, degrees):
        """Convert degrees to cardinal direction (NESW)."""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = round(degrees / 45) % 8
        return directions[index]
