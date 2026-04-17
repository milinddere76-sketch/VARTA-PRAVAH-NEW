import requests
import os

def get_weather():
    """
    Fetches real-time weather data for Mumbai from OpenWeatherMap.
    Requires OPENWEATHER_API_KEY in environment.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    city = "Mumbai"
    
    if not api_key:
        return "Mumbai: 30°C Sunny" # Fallback
        
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if response.status_code == 200:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["main"]
            return f"{city}: {int(temp)}°C {desc}"
        else:
            print(f"⚠️ Weather API Error: {data.get('message')}")
            return "Mumbai: 30°C Clear"
    except Exception as e:
        print(f"⚠️ Weather fetching failed: {e}")
        return "Mumbai: 28°C"
