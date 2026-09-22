from unittest.mock import patch, MagicMock
import pytest

from app.graph import (
    app_graph,
    LOCATION_ERROR_MESSAGE,
    WEATHER_ERROR_MESSAGE,
    NO_SOP_ERROR_MESSAGE
)
from app.weather import LocationNotFoundError, WeatherAPIError

# Mock sample data
MOCK_LOCATION = {
    "name": "Mumbai",
    "latitude": 19.076,
    "longitude": 72.8777,
    "country": "India"
}

MOCK_NORMAL_WEATHER = {
    "temperature_2m": 25.0,
    "apparent_temperature": 26.0,
    "precipitation": 0.0,
    "precipitation_probability": 10.0,
    "wind_speed_10m": 10.0,
    "wind_gusts_10m": 15.0,
    "uv_index": 3.0,
    "visibility": 10000.0
}

MOCK_SEVERE_WEATHER = {
    "temperature_2m": 32.0,
    "apparent_temperature": 36.0,
    "precipitation": 12.0,
    "precipitation_probability": 80.0,
    "wind_speed_10m": 28.0,
    "wind_gusts_10m": 45.0,
    "uv_index": 9.0,
    "visibility": 800.0
}



# 1. Successful deterministic workflow & 10. Graph reaches END successfully
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.compose_response")
def test_successful_deterministic_workflow(mock_compose, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = MOCK_SEVERE_WEATHER
    mock_compose.return_value = "Stay hydrated and avoid high heat outdoor exertion."

    initial_state = {
        "user_message": "Cycling workout in Mumbai",
        "location": "Mumbai"
    }

    result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "test-1"}})

    assert result["response"] == "Stay hydrated and avoid high heat outdoor exertion."
    assert "SOP-003" in result["matched_sop_ids"]
    assert result["selected_sop"]["id"] == "SOP-003"


# 2. Location resolution failure -> exact location fallback
@patch("app.graph.geocode_location")
def test_location_resolution_failure_fallback(mock_geo):
    mock_geo.side_effect = LocationNotFoundError("City not found")

    initial_state = {
        "user_message": "Weather in UnknownCity9999",
        "location": "UnknownCity9999"
    }

    result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "test-2"}})

    assert result["response"] == LOCATION_ERROR_MESSAGE


# 3. Weather API failure -> exact weather fallback
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
def test_weather_api_failure_fallback(mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.side_effect = WeatherAPIError("HTTP 500 Error")

    initial_state = {
        "user_message": "Weather in Mumbai",
        "location": "Mumbai"
    }

    result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "test-3"}})

    assert result["response"] == WEATHER_ERROR_MESSAGE


# 4. No SOP match -> exact no-SOP fallback
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.select_fuzzy_sop")
def test_no_sop_match_fallback(mock_fuzzy, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = MOCK_NORMAL_WEATHER
    mock_fuzzy.return_value = None

    initial_state = {
        "user_message": "Random query in Mumbai",
        "location": "Mumbai"
    }

    result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "test-4"}})

    assert result["response"] == NO_SOP_ERROR_MESSAGE


# 5. Multiple deterministic matches -> highest severity selected
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.compose_response")
def test_multiple_deterministic_matches_highest_severity(mock_compose, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = {
        "temperature_2m": 25.0,
        "apparent_temperature": 26.0,
        "precipitation": 12.0,
        "precipitation_probability": 80.0,
        "wind_speed_10m": 15.0,
        "wind_gusts_10m": 45.0,
        "uv_index": 3.0,
        "visibility": 5000.0
    }
    mock_compose.return_value = "High rain and wind driving warning."

    result = app_graph.invoke({"user_message": "Driving in Mumbai", "location": "Mumbai"}, config={"configurable": {"thread_id": "test-5"}})

    assert result["selected_sop"]["severity"] == "high"
    assert result["selected_sop"]["id"] == "SOP-005"
    assert "SOP-004" in result["matched_sop_ids"]


# 6. Same severity -> first/YAML order selected
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.compose_response")
def test_same_severity_first_yaml_order_selected(mock_compose, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = {
        "temperature_2m": 25.0,
        "apparent_temperature": 26.0,
        "precipitation": 0.0,
        "precipitation_probability": 10.0,
        "wind_speed_10m": 30.0,
        "wind_gusts_10m": 35.0,
        "uv_index": 9.0,
        "visibility": 10000.0
    }
    mock_compose.return_value = "Medium warning response."

    result = app_graph.invoke({"user_message": "Exercise in Mumbai", "location": "Mumbai"}, config={"configurable": {"thread_id": "test-6"}})

    assert result["selected_sop"]["id"] == "SOP-001"


# 7. Fuzzy SOP selected when there are no deterministic matches
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.select_fuzzy_sop")
@patch("app.graph.compose_response")
def test_fuzzy_sop_selected_when_no_deterministic(mock_compose, mock_fuzzy, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = MOCK_NORMAL_WEATHER
    mock_fuzzy.return_value = {
        "id": "SOP-010",
        "name": "Fuzzy Picnic Comfort Advisory",
        "trigger_type": "fuzzy",
        "severity": "low",
        "advice": "Good picnic day."
    }
    mock_compose.return_value = "Picnic looks great today!"

    result = app_graph.invoke({"user_message": "Can I go for a picnic in Mumbai?", "location": "Mumbai"}, config={"configurable": {"thread_id": "test-7"}})

    assert result["selected_sop"]["id"] == "SOP-010"
    assert result["response"] == "Picnic looks great today!"


# 8. Invalid fuzzy SOP ID -> no-SOP path
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.select_fuzzy_sop")
def test_invalid_fuzzy_sop_id_routes_to_no_sop(mock_fuzzy, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = MOCK_NORMAL_WEATHER
    mock_fuzzy.return_value = None

    result = app_graph.invoke({"user_message": "Picnic in Mumbai", "location": "Mumbai"}, config={"configurable": {"thread_id": "test-8"}})

    assert result["response"] == NO_SOP_ERROR_MESSAGE


# 9. Deterministic match does not get overridden by fuzzy LLM selection
@patch("app.graph.geocode_location")
@patch("app.graph.api_fetch_weather")
@patch("app.graph.select_fuzzy_sop")
@patch("app.graph.compose_response")
def test_deterministic_match_not_overridden_by_fuzzy(mock_compose, mock_fuzzy, mock_fetch, mock_geo):
    mock_geo.return_value = MOCK_LOCATION
    mock_fetch.return_value = MOCK_SEVERE_WEATHER
    mock_compose.return_value = "High heat advisory."

    result = app_graph.invoke({"user_message": "Exercise in Mumbai", "location": "Mumbai"}, config={"configurable": {"thread_id": "test-9"}})

    mock_fuzzy.assert_not_called()
    assert result["selected_sop"]["id"] == "SOP-003"


# 10. Focused Location Parsing Unit Tests
@pytest.mark.parametrize("user_message,expected_location", [
    ("Can I go for a walk in Delhi?", "Delhi"),
    ("Can I go for a walk in Delhi, India?", "Delhi"),
    ("Can I go cycling in Mumbai?", "Mumbai"),
    ("What is the weather in Delhi?", "Delhi"),
    ("Can I go for a picnic near Bengaluru?", "Bengaluru"),
])
def test_parse_request_location_extraction(user_message, expected_location):
    from app.graph import parse_request_node
    state = parse_request_node({"user_message": user_message})
    assert state["location"] == expected_location
