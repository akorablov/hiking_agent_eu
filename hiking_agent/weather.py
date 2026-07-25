import random
import time

import requests
from datetime import datetime, date
import statistics


# Identify ourselves to Met.no as required by their terms of service:
# https://api.met.no/doc/TermsOfService - requests without a descriptive User-Agent (app name + a way to contact you) can be blocked outright.
# TODO: replace with your real app name / contact email or repo URL.
METNO_USER_AGENT = "Trail Finder (https://github.com/akorablov/hiking_agent_eu)"


def _fetch_open_meteo(latitude, longitude, retries=3, backoff_base=1.5):
    """
    Fetches hourly weather forecast data from the Open-Meteo API.

    Retries with exponential backoff (+ jitter) on 429 (rate limited) and 5xx responses, since Open-Meteo rate-limits by source IP and a single
    transient failure shouldn't take down the whole pipeline. If the API sends a `Retry-After` header, that's honoured instead of the computed backoff.

    Returns:
        dict: A dictionary containing the API response with weather data, already in the "hourly" shape get_todays_weather_summary expects.

    RuntimeError: If the API call ultimately fails after all retries.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"&hourly=temperature_2m,precipitation_probability,weather_code"
        f"&timezone=auto"
    )

    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=15)

            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After")
                if retry_after is not None:
                    wait = float(retry_after)
                else:
                    wait = (backoff_base ** attempt) + random.uniform(0, 0.5)
                last_error = RuntimeError(
                    f"Open-Meteo returned {response.status_code} for "
                    f"({latitude}, {longitude})"
                )
                if attempt < retries - 1:
                    time.sleep(wait)
                    continue
                break

            response.raise_for_status()
            data = response.json()
            # Validate the response has the expected structure
            if "hourly" not in data:
                raise ValueError(f"Unexpected API response: {str(data)[:200]}")
            return data

        except (requests.exceptions.RequestException, ValueError) as e:
            last_error = e
            if attempt < retries - 1:
                wait = (backoff_base ** attempt) + random.uniform(0, 0.5)
                time.sleep(wait)
                continue
            break

    raise RuntimeError(
        f"Open-Meteo API failed for ({latitude}, {longitude}) after "
        f"{retries} attempts: {last_error}"
    ) from last_error


_METNO_SYMBOL_TO_WMO = {
    "clearsky": 0, "fair": 1, "partlycloudy": 2, "cloudy": 3, "fog": 45,
    "lightrain": 61, "rain": 63, "heavyrain": 65,
    "lightrainshowers": 80, "rainshowers": 80, "heavyrainshowers": 82,
    "lightsleet": 71, "sleet": 73, "heavysleet": 75,
    "lightsleetshowers": 80, "sleetshowers": 80, "heavysleetshowers": 82,
    "lightsnow": 71, "snow": 73, "heavysnow": 75,
    "lightsnowshowers": 85, "snowshowers": 85, "heavysnowshowers": 86,
    "lightrainandthunder": 95, "rainandthunder": 95, "heavyrainandthunder": 96,
    "lightsnowandthunder": 96, "snowandthunder": 96, "heavysnowandthunder": 99,
    "lightsleetandthunder": 95, "sleetandthunder": 95, "heavysleetandthunder": 96,
    "rainshowersandthunder": 95, "heavyrainshowersandthunder": 96,
    "snowshowersandthunder": 96, "heavysnowshowersandthunder": 99,
    "sleetshowersandthunder": 95, "heavysleetshowersandthunder": 96,
}


def _metno_symbol_to_wmo(symbol_code):
    # symbol_code looks like "partlycloudy_day" / "clearsky_night" / "fog"
    base = symbol_code.split("_")[0] if symbol_code else ""
    return _METNO_SYMBOL_TO_WMO.get(base, 3)  # default to "Overcast" if unknown


def _metno_precip_probability(amount_mm):
    # Met.no's locationforecast doesn't expose a precipitation probability field the way Open-Meteo does, so this derives a rough stand-in from forecast precipitation amount. It's an approximation, not a true probability, good enough for a fallback summary.
    if not amount_mm:
        return 0
    if amount_mm <= 0.5:
        return 20
    if amount_mm <= 2:
        return 50
    if amount_mm <= 5:
        return 70
    return 90


def _fetch_metno(latitude, longitude):
    """
    Fetches hourly weather forecast data from Met.no (Norway's national weather service) as a fallback when Open-Meteo is unavailable. Free,
    keyless, and throttled by User-Agent rather than shared IP, so it's unlikely to fail for the same reason at the same time as Open-Meteo.

    Returns:
        dict: Reshaped into the same {"hourly": {...}} structure Open-Meteo eturns, so get_todays_weather_summary() works unchanged.

    Raises:
        RuntimeError: If the API call fails or returns unexpected data.
    """
    url = (
        "https://api.met.no/weatherapi/locationforecast/2.0/compact"
        f"?lat={latitude}&lon={longitude}"
    )
    try:
        response = requests.get(
            url, timeout=15, headers={"User-Agent": METNO_USER_AGENT}
        )
        response.raise_for_status()
        data = response.json()
        timeseries = data["properties"]["timeseries"]

        times, temps, precip_probs, codes = [], [], [], []
        for entry in timeseries:
            details = entry.get("data", {}).get("instant", {}).get("details", {})
            if "air_temperature" not in details:
                continue

            # Prefer the finer-grained next_1_hours block; fall back to next_6_hours further out in the forecast where that's all Met.no provides.
            near = entry["data"].get("next_1_hours") or entry["data"].get("next_6_hours") or {}
            symbol = near.get("summary", {}).get("symbol_code", "")
            precip_amount = near.get("details", {}).get("precipitation_amount", 0)

            times.append(entry["time"])
            temps.append(details["air_temperature"])
            precip_probs.append(_metno_precip_probability(precip_amount))
            codes.append(_metno_symbol_to_wmo(symbol))

        if not times:
            raise ValueError("Met.no response had no usable timeseries entries")

        return {
            "hourly": {
                "time": times,
                "temperature_2m": temps,
                "precipitation_probability": precip_probs,
                "weather_code": codes,
            }
        }
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        raise RuntimeError(f"Met.no API failed for ({latitude}, {longitude}): {e}") from e


def get_weather(latitude, longitude, retries=3, backoff_base=1.5):
    """
    Fetches hourly weather forecast data, preferring Open-Meteo and falling
    back to Met.no if Open-Meteo is unavailable (e.g. rate limited).

    Args:
        latitude (float): The latitude for the weather forecast.
        longitude (float): The longitude for the weather forecast.
        retries (int): Number of Open-Meteo attempts before falling back.
        backoff_base (float): Base seconds for Open-Meteo's exponential backoff.

    Returns:
        dict: A dictionary containing weather data in Open-Meteo's "hourly" shape.

    Raises:
        RuntimeError: If both Open-Meteo and the Met.no fallback fail.
    """
    try:
        return _fetch_open_meteo(latitude, longitude, retries=retries, backoff_base=backoff_base)
    except RuntimeError as primary_error:
        try:
            return _fetch_metno(latitude, longitude)
        except RuntimeError as fallback_error:
            raise RuntimeError(
                f"Both weather sources failed for ({latitude}, {longitude}). "
                f"Open-Meteo: {primary_error} | Met.no: {fallback_error}"
            ) from fallback_error


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
    min_temp = round(min(daylight_temps))
    max_temp = round(max(daylight_temps))
    max_precip = max(daylight_precip_probs) if daylight_precip_probs else 0
    most_common_code = statistics.mode(daylight_codes) if daylight_codes else 0
    weather_description = WMO_CODES.get(most_common_code, "unknown weather")

    summary = (
        f"Today's forecast: {weather_description}, with temperatures ranging from "
        f"{min_temp}°C to {max_temp}°C (average {avg_temp}°C) and a maximum "
        f"precipitation probability of {max_precip}%."
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
