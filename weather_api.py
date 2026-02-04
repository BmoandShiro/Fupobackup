import requests
import datetime
import re

# US ZIP: 5 digits, or 5+4 (12345-6789)
_US_ZIP_RE = re.compile(r"^\s*(\d{5})(?:-\d{4})?\s*$")


def _is_us_zip(query):
    """True if query looks like a US ZIP (5 digits or ZIP+4)."""
    if not query or not isinstance(query, str):
        return False
    return _US_ZIP_RE.match(query.strip()) is not None


def _zip5(query):
    """Extract 5-digit ZIP from input (e.g. 90210 or 90210-1234 -> 90210)."""
    m = _US_ZIP_RE.match((query or "").strip())
    return m.group(1) if m else None


class WeatherAPI:
    def __init__(self):
        self.weather_api_url = "https://api.open-meteo.com/v1/forecast"
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.zippopotam_url = "https://api.zippopotam.us/us"

    def get_current_location(self):
        """Get user's current location based on IP using ip-api.com."""
        try:
            response = requests.get("http://ip-api.com/json/", timeout=10).json()
            if response.get("status") == "success":
                lat = response["lat"]
                lon = response["lon"]
                location = f"{response['city']}, {response['regionName']}, {response['country']}"
                return lat, lon, location
            return None, None, "Unknown Location"
        except Exception as e:
            print(f"IP Geolocation Error: {e}")
            return None, None, "Unknown Location"

    def get_coordinates_from_zip(self, zip5_code):
        """Resolve US ZIP to lat/lon using Zippopotam (reliable for US ZIPs)."""
        zip5_code = (zip5_code or "").strip()
        if len(zip5_code) != 5 or not zip5_code.isdigit():
            return None, None, f"Invalid ZIP: {zip5_code}"
        try:
            r = requests.get(f"{self.zippopotam_url}/{zip5_code}", timeout=10)
            if r.status_code != 200:
                return None, None, f"ZIP {zip5_code} not found."
            data = r.json()
            places = data.get("places") or []
            if not places:
                return None, None, f"ZIP {zip5_code} not found."
            place = places[0]
            lat = float(place.get("latitude", 0))
            lon = float(place.get("longitude", 0))
            name = place.get("place name", "")
            state = place.get("state", "")
            country = data.get("country", "United States")
            location = ", ".join(filter(None, [name, state, country]))
            return lat, lon, location or f"ZIP {zip5_code}"
        except Exception as e:
            print(f"Zippopotam error for {zip5_code}: {e}")
            return None, None, f"Could not resolve ZIP {zip5_code}."

    def get_coordinates(self, query):
        """Resolve city/place name to lat/lon using Open-Meteo Geocoding (no API key)."""
        query = self.clean_location_query(query)
        if not query:
            return None, None, "No location entered."
        try:
            r = requests.get(
                self.geocoding_url,
                params={"name": query, "count": 1},
                timeout=10,
            )
            if r.status_code != 200:
                return None, None, f"Could not look up {query}."
            data = r.json()
            results = data.get("results") or []
            if not results:
                return None, None, f"No results for '{query}'."
            loc = results[0]
            lat = float(loc.get("latitude", 0))
            lon = float(loc.get("longitude", 0))
            name = loc.get("name", "")
            admin1 = loc.get("admin1", "")
            country = loc.get("country", "")
            location = ", ".join(filter(None, [name, admin1, country]))
            return lat, lon, location or query
        except Exception as e:
            print(f"Geocoding error for '{query}': {e}")
            return None, None, f"Could not look up {query}."

    def clean_location_query(self, query):
        """Remove weather-related words from the query."""
        if not query:
            return ""
        cleaned = re.sub(
            r"\b(weather|temperature|forecast|current)\b",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned

    def _resolve_location(self, city):
        """Resolve city/auto/zip to (lat, lon, location_string). Returns (None, None, error_msg) on failure."""
        city = (city or "").strip()
        if not city or city.lower() == "auto":
            return self.get_current_location()
        if _is_us_zip(city):
            return self.get_coordinates_from_zip(_zip5(city))
        return self.get_coordinates(city)

    def get_weather(self, city="auto", spoken_request="", detailed=False):
        """Fetches weather from Open-Meteo. city can be: 'auto', a US ZIP (5 or 5+4), or a city/place name."""
        lat, lon, location = self._resolve_location(city)
        if lat is None or lon is None:
            msg = location or f"Could not get coordinates for {city}."
            return msg, msg, None
        return self._fetch_weather(lat, lon, location, spoken_request, detailed)

    def _fetch_weather(self, lat, lon, location, spoken_request="", detailed=False):
        """Fetch Open-Meteo data for given lat/lon and build response."""
        url = (
            f"{self.weather_api_url}?latitude={lat}&longitude={lon}"
            f"&current_weather=true&timezone=auto"
            f"&hourly=relative_humidity_2m,apparent_temperature,cloudcover,"
            f"dewpoint_2m,precipitation,pressure_msl,windgusts_10m"
            f"&daily=sunrise,sunset"
        )

        try:
            response = requests.get(url).json()

            # 🔎 DEBUG: Print full API response
            print("🔎 Open-Meteo API Response:", response)

            if "current_weather" not in response:
                msg = "Weather data not available."
                return msg, msg, None

            weather = response["current_weather"]
            temp_c = weather["temperature"]
            temp_f = round((temp_c * 9/5) + 32, 1)
            wind_speed_kmh = weather["windspeed"]
            wind_speed_mph = round(wind_speed_kmh * 0.621371, 1)
            wind_dir_degrees = weather["winddirection"]
            wind_dir = self.degrees_to_direction(wind_dir_degrees)

            sunrise_raw = (response.get("daily", {}).get("sunrise") or ["N/A"])[0]
            sunset_raw = (response.get("daily", {}).get("sunset") or ["N/A"])[0]
            if "T" in str(sunrise_raw):
                sunrise = str(sunrise_raw).split("T")[-1][:5]
                sunset = str(sunset_raw).split("T")[-1][:5]
            else:
                sunrise = str(sunrise_raw)[-5:] if len(str(sunrise_raw)) >= 5 else "N/A"
                sunset = str(sunset_raw)[-5:] if len(str(sunset_raw)) >= 5 else "N/A"
            try:
                sunrise_time = datetime.datetime.strptime(sunrise, "%H:%M").strftime("%I:%M %p")
                sunset_time = datetime.datetime.strptime(sunset, "%H:%M").strftime("%I:%M %p")
            except ValueError:
                sunrise_time, sunset_time = sunrise, sunset

            # 🔍 Additional Data for "Detailed Weather"
            feels_like_c = response.get("hourly", {}).get("apparent_temperature", ["N/A"])[0]
            feels_like_f = round((feels_like_c * 9/5) + 32, 1) if isinstance(feels_like_c, (int, float)) else "N/A"

            humidity = response.get("hourly", {}).get("relative_humidity_2m", ["N/A"])[0]
            dew_point_c = response.get("hourly", {}).get("dewpoint_2m", ["N/A"])[0]
            dew_point_f = round((dew_point_c * 9/5) + 32, 1) if isinstance(dew_point_c, (int, float)) else "N/A"

            cloud_cover = response.get("hourly", {}).get("cloudcover", ["N/A"])[0]
            precipitation = response.get("hourly", {}).get("precipitation", ["N/A"])[0]
            pressure = response.get("hourly", {}).get("pressure_msl", ["N/A"])[0]

            gust_speed_kmh = response.get("hourly", {}).get("windgusts_10m", ["N/A"])[0]
            gust_speed_mph = round(gust_speed_kmh * 0.621371, 1) if isinstance(gust_speed_kmh, (int, float)) else "N/A"

            # **SHOW ALL DATA IN TERMINAL**
            print(f"🌍 Weather in {location}")
            print(f"🌡️ Temperature: {temp_f}°F ({temp_c}°C)")
            print(f"🌡️ Feels Like: {feels_like_f}°F ({feels_like_c}°C)")
            print(f"💧 Humidity: {humidity}%")
            print(f"🔵 Dew Point: {dew_point_f}°F ({dew_point_c}°C)")
            print(f"☁️ Cloud Cover: {cloud_cover}%")
            print(f"🌧️ Precipitation: {precipitation} mm")
            print(f"📈 Pressure: {pressure} hPa")
            print(f"💨 Wind Speed: {wind_speed_mph} mph")
            print(f"🌪️ Wind Gusts: {gust_speed_mph} mph")
            print(f"🧭 Wind Direction: {wind_dir}")
            print(f"🌅 Sunrise: {sunrise_time} | 🌇 Sunset: {sunset_time}")

            # **DISPLAY ALL DATA ON DASHBOARD (Always Detailed)**
            response_message = (
                f"🌍 **Weather in {location}**\n"
                f"🌡️ Temperature: {temp_f}°F ({temp_c}°C)\n"
                f"🌡️ Feels Like: {feels_like_f}°F ({feels_like_c}°C)\n"
                f"💧 Humidity: {humidity}%\n"
                f"🔵 Dew Point: {dew_point_f}°F ({dew_point_c}°C)\n"
                f"☁️ Cloud Cover: {cloud_cover}%\n"
                f"🌧️ Precipitation: {precipitation} mm\n"
                f"📈 Pressure: {pressure} hPa\n"
                f"💨 Wind Speed: {wind_speed_mph} mph\n"
                f"🌪️ Wind Gusts: {gust_speed_mph} mph\n"
                f"🧭 Wind Direction: {wind_dir}\n"
                f"🌅 Sunrise: {sunrise_time} | 🌇 Sunset: {sunset_time}"
            )

            # **SPOKEN RESPONSE - Adjusted for "Detailed Weather"**
            spoken_message = f"Weather in {location}: {temp_f}°F, {wind_speed_mph} mph."
    
            if "detailed weather" in spoken_request.lower():
                spoken_message += (
                    f" Feels like {feels_like_f}°F. "
                    f"Humidity {humidity}%. "
                    f"Dew point {dew_point_f}°F. "
                    f"Cloud cover {cloud_cover}%. "
                    f"Precipitation {precipitation} mm. "
                    f"Pressure {pressure} hPa. "
                    f"Gusts up to {gust_speed_mph} mph."
                )

            if "sunrise" in spoken_request.lower():
                spoken_message += f" Sunrise is at {sunrise_time}."
            if "sunset" in spoken_request.lower():
                spoken_message += f" Sunset is at {sunset_time}."

            return response_message, spoken_message, location

        except Exception as e:
            err = f"Error fetching weather data: {e}"
            return err, err, None





    def degrees_to_direction(self, degrees):
        """Convert degrees to cardinal direction (NESW)."""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = round(degrees / 45) % 8
        return directions[index]
