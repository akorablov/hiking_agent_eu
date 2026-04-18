import requests

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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,precipitation_probability,weathercode"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

from datetime import datetime, date
import statistics

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

    Args:
        weather_data (dict): The raw weather data from the Open-Meteo API.

    Returns:
        str: A human-readable summary of the weather for today (8 AM - 5 PM),
             or an error message if data is unavailable.
    """
    hourly = weather_data.get("hourly", {})
    times = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    precip_probs = hourly.get("precipitation_probability", [])
    weather_codes = hourly.get("weathercode", [])

    daylight_temps = []
    daylight_precip_probs = []
    daylight_codes = []

    today_str = date.today().isoformat()

    for i, dt_str in enumerate(times):
        dt_obj = datetime.fromisoformat(dt_str)
        # Filter for today between 8 AM and 5 PM (17:00)
        if dt_obj.date() == date.today() and 8 <= dt_obj.hour <= 17:
            daylight_temps.append(temperatures[i])
            daylight_precip_probs.append(precip_probs[i])
            daylight_codes.append(weather_codes[i])

    if not daylight_temps:
        return "Could not get a weather summary for today's daylight hours."

    # Calculate summary statistics
    avg_temp = round(statistics.mean(daylight_temps))
    max_precip = max(daylight_precip_probs)
    most_common_code = statistics.mode(daylight_codes)
    weather_description = WMO_CODES.get(most_common_code, "unknown weather")

    summary = f"Today's forecast: {weather_description}, with an average temperature of {avg_temp}°C and a maximum precipitation probability of {max_precip}%."
    return summary

if __name__ == '__main__':
    # Example usage
    latitude = 52.52
    longitude = 13.41
    weather_data = get_weather(latitude, longitude)
    summary = get_todays_weather_summary(weather_data)
    print(summary)
