import requests
from datetime import datetime, date
import statistics


def get_weather(latitude, longitude):
    """
    Fetches hourly weather forecast data from the Open-Meteo API.

    Args:
        latitude (float): The latitude for the weather forecast.
        longitude (float): The longitude for the weather forecast.

    Returns:
        dict: A dictionary containing the API response with weather data,
              or None if an error occurs.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"&hourly=temperature_2m,precipitation_probability,weather_code"
        f"&timezone=auto"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None


# WMO Weather interpretation codes
WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def get_todays_weather_summary(weather_data):
    """
    Processes hourly weather data to create a concise summary for today's daylight hours.
    Falls back to the next available hours if today's daylight window has no data
    (e.g. if the API returns data starting from a different day due to timezone).

    Args:
        weather_data (dict): The raw weather data from the Open-Meteo API.

    Returns:
        str: A human-readable summary of the weather, or an error message
             if data is unavailable.
    """
    hourly = weather_data.get("hourly", {})
    times = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    precip_probs = hourly.get("precipitation_probability", [])
    # Support both the current ("weather_code") and legacy ("weathercode") key names
    weather_codes = hourly.get("weather_code", hourly.get("weathercode", []))

    if not times or not temperatures:
        return "Weather data is currently unavailable."

    daylight_temps = []
    daylight_precip_probs = []
    daylight_codes = []

    for i, dt_str in enumerate(times):
        try:
            dt_obj = datetime.fromisoformat(dt_str)
        except ValueError:
            continue
        if dt_obj.date() == date.today() and 8 <= dt_obj.hour <= 17:
            daylight_temps.append(temperatures[i])
            daylight_precip_probs.append(precip_probs[i] if i < len(precip_probs) else 0)
            daylight_codes.append(weather_codes[i] if i < len(weather_codes) else 0)

    # Fallback: if today's 08:00-17:00 window has no data, use the first 10 available hours
    if not daylight_temps and temperatures:
        daylight_temps = temperatures[:10]
        daylight_precip_probs = precip_probs[:10] if precip_probs else [0] * len(daylight_temps)
        daylight_codes = weather_codes[:10] if weather_codes else [0] * len(daylight_temps)

    if not daylight_temps:
        return "Could not get a weather summary for today."

    avg_temp = round(statistics.mean(daylight_temps))
    max_precip = max(daylight_precip_probs) if daylight_precip_probs else 0
    most_common_code = statistics.mode(daylight_codes) if daylight_codes else 0
    weather_description = WMO_CODES.get(most_common_code, "unknown weather")

    summary = (
        f"Today's forecast: {weather_description}, with an average temperature of "
        f"{avg_temp}°C and a maximum precipitation probability of {max_precip}%."
    )
    return summary


if __name__ == '__main__':
    latitude = 52.52
    longitude = 13.41
    weather_data = get_weather(latitude, longitude)
    if weather_data:
        summary = get_todays_weather_summary(weather_data)
        print(summary)
    else:
        print("Failed to fetch weather data.")
