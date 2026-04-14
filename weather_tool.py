"""
Weather Tool — OpenWeatherMap API
-----------------------------------
Gets the current weather and 5-day forecast for any city.
Free tier — no credit card, no usage limits for basic forecasts.

Setup:
  1. Sign up free at https://openweathermap.org/api
  2. Go to API Keys tab in your account dashboard
  3. Copy your key (takes ~10 mins to activate after signup)
  4. pip3 install requests
  5. export OPENWEATHER_API_KEY="your_key_here"
"""

import os
import requests
from langchain.tools import tool


BASE_URL = "https://api.openweathermap.org/data/2.5"


# ── Core tool functions ────────────────────────────────────────────────────────

def get_current_weather(city: str) -> dict:
    """
    Get current weather for a city.

    Args:
        city: City name e.g. "Tokyo" or "Tokyo,JP"

    Returns:
        Dict with temperature, condition, humidity, wind speed.

    Example:
        >>> weather = get_current_weather("Tokyo")
        >>> print(weather["temp"])
        '28°C'
    """
    params = {
        "q":     city,
        "appid": os.environ["OPENWEATHER_API_KEY"],
        "units": "metric",   # change to "imperial" for Fahrenheit
    }

    try:
        res  = requests.get(f"{BASE_URL}/weather", params=params)
        data = res.json()

        if res.status_code != 200:
            return {"error": data.get("message", "Unknown error")}

        return {
            "city":        data["name"],
            "country":     data["sys"]["country"],
            "temp":        f"{round(data['main']['temp'])}°C",
            "feels_like":  f"{round(data['main']['feels_like'])}°C",
            "condition":   data["weather"][0]["description"].capitalize(),
            "humidity":    f"{data['main']['humidity']}%",
            "wind":        f"{round(data['wind']['speed'] * 3.6)} km/h",  # m/s → km/h
            "visibility":  f"{data.get('visibility', 0) // 1000} km",
        }

    except Exception as e:
        return {"error": str(e)}


def get_forecast(city: str, days: int = 5) -> list[dict]:
    """
    Get a multi-day weather forecast for a city.
    OpenWeatherMap free tier gives 5 days in 3-hour intervals.
    We collapse it to one summary per day.

    Args:
        city: City name e.g. "Tokyo"
        days: Number of days to forecast (max 5)

    Returns:
        List of daily forecast dicts.
    """
    params = {
        "q":     city,
        "appid": os.environ["OPENWEATHER_API_KEY"],
        "units": "metric",
        "cnt":   days * 8,   # 8 x 3-hour slots per day
    }

    try:
        res  = requests.get(f"{BASE_URL}/forecast", params=params)
        data = res.json()

        if res.status_code != 200:
            return [{"error": data.get("message", "Unknown error")}]

        # Group by date and take midday reading (12:00) as representative
        daily = {}
        for entry in data["list"]:
            date = entry["dt_txt"].split(" ")[0]
            time = entry["dt_txt"].split(" ")[1]
            if date not in daily or time == "12:00:00":
                daily[date] = {
                    "date":      date,
                    "temp_high": f"{round(entry['main']['temp_max'])}°C",
                    "temp_low":  f"{round(entry['main']['temp_min'])}°C",
                    "condition": entry["weather"][0]["description"].capitalize(),
                    "humidity":  f"{entry['main']['humidity']}%",
                    "wind":      f"{round(entry['wind']['speed'] * 3.6)} km/h",
                }

        return list(daily.values())[:days]

    except Exception as e:
        return [{"error": str(e)}]


# ── LangChain tool wrappers ────────────────────────────────────────────────────

@tool
def weather_tool(city: str) -> str:
    """
    Get the current weather for any city.
    Use this when the user asks about weather at their destination,
    what to pack, or whether conditions are good for outdoor activities.
    Input is a city name like 'Tokyo' or 'Paris'.
    """
    w = get_current_weather(city)

    if "error" in w:
        return f"Could not get weather for {city}: {w['error']}"

    return (
        f"Current weather in {w['city']}, {w['country']}:\n"
        f"  Temperature:  {w['temp']} (feels like {w['feels_like']})\n"
        f"  Condition:    {w['condition']}\n"
        f"  Humidity:     {w['humidity']}\n"
        f"  Wind:         {w['wind']}\n"
        f"  Visibility:   {w['visibility']}"
    )


@tool
def forecast_tool(city: str) -> str:
    """
    Get a 5-day weather forecast for any city.
    Use this when the user is planning a multi-day trip and wants to
    know what the weather will be like each day.
    Input is a city name like 'Tokyo' or 'Paris'.
    """
    forecast = get_forecast(city)

    if not forecast or "error" in forecast[0]:
        return f"Could not get forecast: {forecast[0].get('error', 'Unknown error')}"

    lines = [f"5-day forecast for {city}:"]
    for day in forecast:
        lines.append(
            f"  {day['date']} | High: {day['temp_high']} Low: {day['temp_low']} | "
            f"{day['condition']} | Humidity: {day['humidity']} | Wind: {day['wind']}"
        )
    return "\n".join(lines)


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing OpenWeatherMap...\n")

    print("--- Current weather ---")
    current = get_current_weather("Tokyo")
    print(current)

    print("\n--- 5-day forecast ---")
    forecast = get_forecast("Tokyo")
    for day in forecast:
        print(day)

    print("\n--- LangChain tool output (current) ---")
    print(weather_tool.run({"city": "Tokyo"}))

    print("\n--- LangChain tool output (forecast) ---")
    print(forecast_tool.run({"city": "Tokyo"}))
