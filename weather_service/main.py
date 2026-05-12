import os
import csv
import httpx
import asyncio
from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from geopy.geocoders import Nominatim
from shared.models import SignalBundle

app = FastAPI(title="Syngenta Coordinate-Based Weather API")

PEST_ALERTS_FILE = os.path.join(os.path.dirname(__file__), "pest_alerts.csv")
geolocator = Nominatim(user_agent="krishimitra_ai_hackathon")

# Simple in-memory cache
BASELINE_CACHE = {}

# Shortcut seasonal normals for demo fallback
SEASONAL_NORMALS = {
    "Chennai": {"avg_temp_may": 29, "avg_rainfall_may": 35},
    "Ahmedabad": {"avg_temp_may": 33, "avg_rainfall_may": 5},
    "Thanjavur": {"avg_temp_may": 30, "avg_rainfall_may": 45},
    "Guntur": {"avg_temp_may": 32, "avg_rainfall_may": 40}
}

async def get_district_from_coords(lat: float, lon: float):
    """Reverse geocode lat/lon to find district and state name."""
    try:
        loop = asyncio.get_event_loop()
        location = await loop.run_in_executor(None, lambda: geolocator.reverse((lat, lon)))
        if location:
            address = location.raw.get('address', {})
            district = address.get('district') or address.get('city') or address.get('county') or address.get('suburb')
            state = address.get('state')
            return district, state
    except Exception: pass
    return None, None

async def get_historical_baselines(lat: float, lon: float, district: str = None):
    """Fetch historical baselines from NASA POWER or Fallback."""
    cache_key = f"{round(lat, 2)},{round(lon, 2)}"
    if cache_key in BASELINE_CACHE: return BASELINE_CACHE[cache_key]

    url = f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=T2M,PRECTOTCORR&community=AG&longitude={lon}&latitude={lat}&format=JSON"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            may_temp = data['properties']['parameter']['T2M']['5']
            may_rain = data['properties']['parameter']['PRECTOTCORR']['5']
            res = (float(may_temp), float(may_rain))
            BASELINE_CACHE[cache_key] = res
            return res
        except Exception:
            if district and district in SEASONAL_NORMALS:
                n = SEASONAL_NORMALS[district]
                return n['avg_temp_may'], n['avg_rainfall_may']
            return 30.0, 50.0

async def get_current_weather(lat: float, lon: float):
    """Fetch hourly conditions from Open-Meteo for 7-day average computation."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m"
        "&hourly=relative_humidity_2m,temperature_2m"
        "&daily=precipitation_sum&forecast_days=7&timezone=auto"
    )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            curr_temp = data['current']['temperature_2m']
            hourly_humidity = data['hourly']['relative_humidity_2m']
            humidity_7d_avg = sum(hourly_humidity) / len(hourly_humidity)
            rain_7d = sum(data['daily']['precipitation_sum'])
            
            return float(curr_temp), float(humidity_7d_avg), float(rain_7d)
        except Exception:
            return 32.0, 65.0, 10.0

def get_pest_risk(district: str):
    try:
        with open(PEST_ALERTS_FILE, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if district and row['district'].lower() in district.lower():
                    return row['pest_name'], row['risk_level']
    except Exception: pass
    return "None", "low"

@app.get("/signals/weather", response_model=SignalBundle)
async def get_weather_signals(lat: float = Query(...), lon: float = Query(...)):
    """Primary weather endpoint: specific to latitude and longitude."""
    # 1. Reverse Geocode for District/State context
    district, state = await get_district_from_coords(lat, lon)
    
    # 2. Fetch Signals and Baselines
    (hist_temp, hist_rain), (curr_temp, humidity_avg, rain_7d) = await asyncio.gather(
        get_historical_baselines(lat, lon, district),
        get_current_weather(lat, lon)
    )
    pest_name, pest_risk = get_pest_risk(district)
    
    temp_anomaly = curr_temp - hist_temp
    weekly_hist_rain = hist_rain / 4.0
    rain_dev_pct = ((rain_7d - weekly_hist_rain) / weekly_hist_rain * 100) if weekly_hist_rain > 0 else 0.0
    
    return SignalBundle(
        district=district,
        state=state,
        humidity_7d_avg=round(humidity_avg, 1),
        rainfall_deviation_pct=round(rain_dev_pct, 1),
        temperature_anomaly=round(temp_anomaly, 1),
        pest_risk_level=pest_risk,
        active_pest=pest_name,
        weather_anomaly_flag=abs(temp_anomaly) > 3.5 or abs(rain_dev_pct) > 50.0
    )

@app.get("/debug/weather")
async def debug_weather(lat: float = Query(...), lon: float = Query(...)):
    """Debug info for a specific coordinate."""
    district, state = await get_district_from_coords(lat, lon)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m&hourly=relative_humidity_2m&daily=precipitation_sum&timezone=auto"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    return {
        "resolved_location": {"district": district, "state": state},
        "open_meteo_url": url,
        "raw_response": data
    }

@app.get("/health")
def health():
    return {"status": "ok", "module": "M4"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
