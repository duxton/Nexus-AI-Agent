import os
import httpx
import json
from typing import Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class WeatherData(BaseModel):
    location: str
    temperature_c: float
    temperature_f: float
    condition: str
    humidity: int
    wind_kph: float
    wind_direction: str
    feels_like_c: float
    uv_index: float
    visibility_km: float
    last_updated: str

class WeatherForecast(BaseModel):
    date: str
    max_temp_c: float
    min_temp_c: float
    condition: str
    chance_of_rain: int
    max_wind_kph: float

class WeatherAgent:
    """Agent for retrieving real-time weather data for Malaysia using WeatherAPI"""

    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY")
        if not self.api_key:
            raise ValueError("WEATHER_API_KEY environment variable is required")

        self.base_url = "https://api.weatherapi.com/v1"
        self.default_location = "Kuala Lumpur, Malaysia"

    async def get_current_weather(self, location: str = None) -> Dict[str, Any]:
        """Get current weather for specified location or default to KL"""
        print("Get current weather called")
        if not location:
            location = self.default_location

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/current.json",
                    params={
                        "key": self.api_key,
                        "q": location,
                        "aqi": "yes"  # Include air quality data
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    print(data)
                    return self._format_current_weather(data)
                else:
                    error_data = response.json() if response.content else {}
                    print("Weather API error:", response.status_code, error_data)
                    return {
                        "error": f"Weather API error: {response.status_code}",
                        "details": error_data.get("error", {}).get("message", "Unknown error")
                    }

        except httpx.TimeoutException:
            return {"error": "Weather API request timed out"}
        except Exception as e:
            print("Exception in get_current_weather:", str(e))
            return {"error": f"Failed to fetch weather data: {str(e)}"}

    async def get_weather_forecast(self, days: int = 3, location: str = None) -> Dict[str, Any]:
        """Get weather forecast for specified days (1-10 days)"""
        if not location:
            location = self.default_location

        # Limit days to API constraints
        days = max(1, min(days, 10))

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/forecast.json",
                    params={
                        "key": self.api_key,
                        "q": location,
                        "days": days,
                        "aqi": "yes"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._format_forecast_weather(data)
                else:
                    error_data = response.json() if response.content else {}
                    return {
                        "error": f"Weather API error: {response.status_code}",
                        "details": error_data.get("error", {}).get("message", "Unknown error")
                    }

        except httpx.TimeoutException:
            return {"error": "Weather API request timed out"}
        except Exception as e:
            return {"error": f"Failed to fetch forecast data: {str(e)}"}

    def _format_current_weather(self, data: Dict) -> Dict[str, Any]:
        """Format current weather data into a readable response"""
        try:
            print("Formatting weather data...")
            location = data["location"]
            current = data["current"]

            weather_data = WeatherData(
                location=f"{location['name']}, {location['region']}, {location['country']}",
                temperature_c=current["temp_c"],
                temperature_f=current["temp_f"],
                condition=current["condition"]["text"],
                humidity=current["humidity"],
                wind_kph=current["wind_kph"],
                wind_direction=current["wind_dir"],
                feels_like_c=current["feelslike_c"],
                uv_index=current.get("uv", 0),  # Default to 0 if not available
                visibility_km=current["vis_km"],
                last_updated=current["last_updated"]
            )

            # Format into human-readable text
            formatted_response = f"""🌤️ **Current Weather for {weather_data.location}**

**Temperature:** {weather_data.temperature_c}°C ({weather_data.temperature_f}°F)
**Condition:** {weather_data.condition}
**Feels like:** {weather_data.feels_like_c}°C
**Humidity:** {weather_data.humidity}%
**Wind:** {weather_data.wind_kph} km/h {weather_data.wind_direction}
**UV Index:** {weather_data.uv_index}
**Visibility:** {weather_data.visibility_km} km

*Last updated: {weather_data.last_updated}*"""

            print("Formatted response ready:", formatted_response[:100] + "...")
            return {
                "success": True,
                "formatted_response": formatted_response,
                "raw_data": weather_data.dict()
            }

        except KeyError as e:
            print("KeyError in formatting:", str(e))
            return {"error": f"Unexpected weather data format: missing {str(e)}"}
        except Exception as e:
            print("Exception in formatting:", str(e))
            return {"error": f"Error formatting weather data: {str(e)}"}

    def _format_forecast_weather(self, data: Dict) -> Dict[str, Any]:
        """Format forecast weather data into a readable response"""
        try:
            location = data["location"]
            forecast_days = data["forecast"]["forecastday"]

            forecasts = []
            for day_data in forecast_days:
                day = day_data["day"]
                forecasts.append(WeatherForecast(
                    date=day_data["date"],
                    max_temp_c=day["maxtemp_c"],
                    min_temp_c=day["mintemp_c"],
                    condition=day["condition"]["text"],
                    chance_of_rain=day["daily_chance_of_rain"],
                    max_wind_kph=day["maxwind_kph"]
                ))

            # Format into human-readable text
            location_str = f"{location['name']}, {location['region']}, {location['country']}"
            formatted_response = f"📅 **{len(forecasts)}-Day Weather Forecast for {location_str}**\n\n"

            for forecast in forecasts:
                date_obj = datetime.strptime(forecast.date, "%Y-%m-%d")
                day_name = date_obj.strftime("%A, %B %d")

                formatted_response += f"""**{day_name}**
• {forecast.condition}
• High: {forecast.max_temp_c}°C, Low: {forecast.min_temp_c}°C
• Chance of rain: {forecast.chance_of_rain}%
• Max wind: {forecast.max_wind_kph} km/h

"""

            return {
                "success": True,
                "formatted_response": formatted_response.strip(),
                "raw_data": [f.dict() for f in forecasts]
            }

        except KeyError as e:
            return {"error": f"Unexpected forecast data format: missing {str(e)}"}

    async def search_weather_locations(self, query: str) -> Dict[str, Any]:
        """Search for weather locations based on query"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/search.json",
                    params={
                        "key": self.api_key,
                        "q": query
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        return {"error": f"No locations found for '{query}'"}

                    locations = []
                    for loc in data[:5]:  # Limit to top 5 results
                        locations.append({
                            "name": loc["name"],
                            "region": loc["region"],
                            "country": loc["country"],
                            "lat": loc["lat"],
                            "lon": loc["lon"]
                        })

                    formatted_response = f"📍 **Locations matching '{query}':**\n\n"
                    for i, loc in enumerate(locations, 1):
                        formatted_response += f"{i}. {loc['name']}, {loc['region']}, {loc['country']}\n"

                    return {
                        "success": True,
                        "formatted_response": formatted_response.strip(),
                        "locations": locations
                    }
                else:
                    error_data = response.json() if response.content else {}
                    return {
                        "error": f"Location search error: {response.status_code}",
                        "details": error_data.get("error", {}).get("message", "Unknown error")
                    }

        except Exception as e:
            return {"error": f"Failed to search locations: {str(e)}"}

    def get_weather_summary(self, location: str = None) -> str:
        """Get a quick weather summary text for chat responses"""
        if not location:
            location = self.default_location

        return f"I can provide current weather conditions and forecasts for {location} using real-time data from WeatherAPI. Ask me about:\n" \
               f"• Current weather conditions\n" \
               f"• 3-day or weekly forecast\n" \
               f"• Weather for specific Malaysian cities\n" \
               f"• Temperature, humidity, wind conditions"

# Create global weather agent instance
weather_agent = WeatherAgent() if os.getenv("WEATHER_API_KEY") else None