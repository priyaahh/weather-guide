import requests

# Base & specific exceptions for weather module
class WeatherError(Exception):
    """Base exception for all weather-related errors."""
    pass


class LocationNotFoundError(WeatherError):
    """Raised when a location name cannot be resolved by the geocoding API."""
    pass


class WeatherAPIError(WeatherError):
    """Raised when an external API call fails (HTTP errors, timeouts, connection issues)."""
    pass


class MalformedWeatherResponseError(WeatherError):
    """Raised when the weather API response is missing required data fields."""
    pass


GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

REQUIRED_WEATHER_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "precipitation_probability",
    "wind_speed_10m",
    "wind_gusts_10m",
    "uv_index",
    "visibility",
]


def geocode_location(location: str) -> dict:
    """
    Resolves a city or place name to latitude and longitude using Open-Meteo Geocoding API.

    Args:
        location (str): Name of the city or location (e.g. "Mumbai", "London").

    Returns:
        dict: Location details with keys 'name', 'latitude', 'longitude', 'country'.

    Raises:
        ValueError: If location parameter is empty or blank.
        LocationNotFoundError: If no matching location is returned.
        WeatherAPIError: If the HTTP request fails.
    """
    if not location or not location.strip():
        raise ValueError("Location string cannot be empty.")

    params = {
        "name": location.strip(),
        "count": 1,
        "language": "en",
        "format": "json"
    }

    try:
        response = requests.get(GEOCODING_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise WeatherAPIError(f"Geocoding API request failed for '{location}': {exc}") from exc
    except ValueError as exc:
        raise MalformedWeatherResponseError(f"Invalid JSON returned by Geocoding API: {exc}") from exc

    results = data.get("results")
    if not results or not isinstance(results, list) or len(results) == 0:
        raise LocationNotFoundError(f"Location '{location}' not found.")

    top_result = results[0]
    return {
        "name": top_result.get("name", location),
        "latitude": float(top_result["latitude"]),
        "longitude": float(top_result["longitude"]),
        "country": top_result.get("country", "")
    }


def fetch_weather(latitude: float, longitude: float) -> dict:
    """
    Fetches live weather data for given coordinates from Open-Meteo Forecast API.

    Args:
        latitude (float): Latitude coordinate.
        longitude (float): Longitude coordinate.

    Returns:
        dict: Clean dictionary containing only the required 8 weather fields.

    Raises:
        WeatherAPIError: If the HTTP request fails.
        MalformedWeatherResponseError: If required weather fields are missing.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(REQUIRED_WEATHER_FIELDS)
    }

    try:
        response = requests.get(FORECAST_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise WeatherAPIError(f"Weather API request failed for ({latitude}, {longitude}): {exc}") from exc
    except ValueError as exc:
        raise MalformedWeatherResponseError(f"Invalid JSON returned by Weather API: {exc}") from exc

    current = data.get("current")
    if not isinstance(current, dict):
        raise MalformedWeatherResponseError("Weather API response missing 'current' data section.")

    weather_data = {}
    for field in REQUIRED_WEATHER_FIELDS:
        if field not in current or current[field] is None:
            raise MalformedWeatherResponseError(f"Missing required weather field in response: '{field}'")
        weather_data[field] = current[field]

    return weather_data


def get_weather_for_location(location: str) -> dict:
    """
    Convenience function combining geocoding and weather fetching for a location name.

    Args:
        location (str): Name of the city or location.

    Returns:
        dict: Dictionary containing 'location' details and 'weather' metrics.
    """
    geo = geocode_location(location)
    weather = fetch_weather(geo["latitude"], geo["longitude"])
    return {
        "location": geo,
        "weather": weather
    }
