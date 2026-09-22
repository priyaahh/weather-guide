from unittest.mock import patch, MagicMock
import pytest
import requests

from app.weather import (
    geocode_location,
    fetch_weather,
    get_weather_for_location,
    LocationNotFoundError,
    WeatherAPIError,
    MalformedWeatherResponseError,
    REQUIRED_WEATHER_FIELDS
)


# Mock sample data
MOCK_GEO_SUCCESS_RESPONSE = {
    "results": [
        {
            "name": "Mumbai",
            "latitude": 19.076,
            "longitude": 72.8777,
            "country": "India"
        }
    ]
}

MOCK_GEO_EMPTY_RESPONSE = {
    "results": []
}

MOCK_WEATHER_SUCCESS_RESPONSE = {
    "current": {
        "temperature_2m": 31.5,
        "apparent_temperature": 36.2,
        "precipitation": 0.0,
        "precipitation_probability": 15,
        "wind_speed_10m": 12.4,
        "wind_gusts_10m": 18.0,
        "uv_index": 7.5,
        "visibility": 10000.0
    }
}

MOCK_WEATHER_MALFORMED_RESPONSE = {
    "current": {
        "temperature_2m": 31.5
        # missing required apparent_temperature and other fields
    }
}


# --- Geocoding Tests ---

@patch("requests.get")
def test_geocode_location_success(mock_get):
    """Test 1: Successful location resolution."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = MOCK_GEO_SUCCESS_RESPONSE
    mock_get.return_value = mock_response

    result = geocode_location("Mumbai")

    assert result["name"] == "Mumbai"
    assert result["latitude"] == 19.076
    assert result["longitude"] == 72.8777
    assert result["country"] == "India"
    mock_get.assert_called_once()


@patch("requests.get")
def test_geocode_location_not_found(mock_get):
    """Test 2: Location not found raises LocationNotFoundError."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = MOCK_GEO_EMPTY_RESPONSE
    mock_get.return_value = mock_response

    with pytest.raises(LocationNotFoundError) as exc_info:
        geocode_location("NonExistentCity12345")

    assert "not found" in str(exc_info.value).lower()


def test_geocode_empty_location_raises_value_error():
    """Test edge case: Empty location input raises ValueError."""
    with pytest.raises(ValueError):
        geocode_location("   ")


@patch("requests.get")
def test_geocode_api_failure(mock_get):
    """Test HTTP failure during geocoding raises WeatherAPIError."""
    mock_get.side_effect = requests.RequestException("Connection timeout")

    with pytest.raises(WeatherAPIError) as exc_info:
        geocode_location("Mumbai")

    assert "geocoding api request failed" in str(exc_info.value).lower()


# --- Weather Fetching Tests ---

@patch("requests.get")
def test_fetch_weather_success(mock_get):
    """Test 3: Successful weather response parsing."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = MOCK_WEATHER_SUCCESS_RESPONSE
    mock_get.return_value = mock_response

    weather = fetch_weather(19.076, 72.8777)

    for field in REQUIRED_WEATHER_FIELDS:
        assert field in weather

    assert weather["temperature_2m"] == 31.5
    assert weather["uv_index"] == 7.5
    assert weather["visibility"] == 10000.0


@patch("requests.get")
def test_fetch_weather_api_failure(mock_get):
    """Test 4: Weather API HTTP error raises WeatherAPIError."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
    mock_get.return_value = mock_response

    with pytest.raises(WeatherAPIError) as exc_info:
        fetch_weather(19.076, 72.8777)

    assert "weather api request failed" in str(exc_info.value).lower()


@patch("requests.get")
def test_fetch_weather_missing_field_malformed(mock_get):
    """Test 5: Missing required weather field raises MalformedWeatherResponseError."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = MOCK_WEATHER_MALFORMED_RESPONSE
    mock_get.return_value = mock_response

    with pytest.raises(MalformedWeatherResponseError) as exc_info:
        fetch_weather(19.076, 72.8777)

    assert "missing required weather field" in str(exc_info.value).lower()


@patch("app.weather.fetch_weather")
@patch("app.weather.geocode_location")
def test_get_weather_for_location_integration(mock_geo, mock_weather):
    """Test convenience wrapper function get_weather_for_location."""
    mock_geo.return_value = {"name": "Mumbai", "latitude": 19.076, "longitude": 72.8777, "country": "India"}
    mock_weather.return_value = MOCK_WEATHER_SUCCESS_RESPONSE["current"]

    res = get_weather_for_location("Mumbai")

    assert res["location"]["name"] == "Mumbai"
    assert res["weather"]["temperature_2m"] == 31.5
