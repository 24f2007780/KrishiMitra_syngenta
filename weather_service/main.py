import os
import csv
import httpx
import asyncio
from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from geopy.geocoders import Nominatim
from shared.models import SignalBundle
from datetime import datetime

app = FastAPI(title="Syngenta Coordinate-Based Weather API")

PEST_ALERTS_FILE = os.path.join(os.path.dirname(__file__), "pest_alerts.csv")
geolocator = Nominatim(user_agent="krishimitra_ai_hackathon")

# Simple in-memory cache
BASELINE_CACHE = {}
WEATHER_CACHE = {}
WEATHER_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "dataset", "weather_cache.csv"
)

def load_weather_cache():
    global WEATHER_CACHE
    if os.path.exists(WEATHER_CACHE_PATH):
        try:
            with open(WEATHER_CACHE_PATH, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    loc_key = row.get("location_key")
                    if loc_key:
                        pest_val = row.get("pest_risk") or row.get("pest_risk_level") or "low"
                        if pest_val in ["low", "medium", "high"]:
                            pest_risk_float = {"high": 0.8, "medium": 0.5, "low": 0.2}[pest_val]
                        else:
                            try:
                                pest_risk_float = float(pest_val)
                            except ValueError:
                                pest_risk_float = 0.2

                        raw_wa = row.get("weather_anomaly") 
                        try:
                            raw_wa_val = float(raw_wa) if raw_wa is not None else 0.0
                            if 0.0 <= raw_wa_val <= 1.0:
                                wa_val = raw_wa_val
                            else:
                                wa_val = min(abs(raw_wa_val) / 5.0, 1.0)
                        except ValueError:
                            wa_val = 0.2

                        WEATHER_CACHE[loc_key] = {
                            "district": row.get("district"),
                            "state": row.get("state"),
                            "humidity_7d_avg": float(row.get("humidity_7d_avg") or 0.0),
                            "rainfall_deviation_pct": float(row.get("rainfall_deviation_pct") or 0.0),
                            "weather_anomaly": wa_val,
                            "pest_risk": pest_risk_float,
                            "active_pest": row.get("active_pest") or "None",
                            "weather_anomaly_flag": str(row.get("weather_anomaly_flag")).lower() == "true",
                        }
            print(f"Loaded {len(WEATHER_CACHE)} weather cache entries.")
        except Exception as e:
            print(f"Error loading weather cache: {e}")

@app.on_event("startup")
def startup_event():
    load_weather_cache()

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

BASELINE_CACHE = {}

async def get_historical_baselines(lat: float, lon: float):

    try:

        month_key = datetime.utcnow().strftime("%b").upper()

        cache_key = f"{round(lat,2)},{round(lon,2)}:{month_key}"

        if cache_key in BASELINE_CACHE:
            print("DEBUG: CACHE HIT")
            return BASELINE_CACHE[cache_key]

        url = (
            "https://power.larc.nasa.gov/api/temporal/climatology/point"
            f"?parameters=T2M,PRECTOTCORR"
            f"&community=AG"
            f"&longitude={lon}"
            f"&latitude={lat}"
            f"&format=JSON"
        )

        print(f"DEBUG URL: {url}")

        async with httpx.AsyncClient() as client:

            response = await client.get(url, timeout=20)

            print(f"DEBUG STATUS: {response.status_code}")

            response.raise_for_status()

            data = response.json()

            print("DEBUG RESPONSE RECEIVED")

            params = data["properties"]["parameter"]

            print(f"DEBUG PARAM KEYS: {params.keys()}")

            temp = params["T2M"][month_key]
            rain = params["PRECTOTCORR"][month_key]

            print(f"DEBUG TEMP={temp} RAIN={rain}")

            result = (float(temp), float(rain))

            BASELINE_CACHE[cache_key] = result

            return result

    except Exception as e:

        print("NASA POWER ERROR")
        print(type(e))
        print(str(e))

        raise
        
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

def build_signal_bundle(
    district: str,
    state: str,
    humidity_avg: float,
    rain_7d: float,
    curr_temp: float,
    hist_temp: float,
    hist_rain: float,
    pest_name: str,
    pest_risk: str
) -> SignalBundle:
    temp_anomaly = curr_temp - hist_temp
    weekly_hist_rain = hist_rain / 4.0
    rain_dev_pct = ((rain_7d - weekly_hist_rain) / weekly_hist_rain * 100) if weekly_hist_rain > 0 else 0.0
    
    if isinstance(pest_risk, (int, float)):
        pest_risk_float = float(pest_risk)
    else:
        pest_map = {"high": 0.8, "medium": 0.5, "low": 0.2}
        pest_risk_float = pest_map.get(str(pest_risk).lower(), 0.2)

    # Map temp & rain anomalies to a [0, 1] weather anomaly value
    temp_dev = min(abs(temp_anomaly) / 5.0, 1.0)
    rain_dev = min(abs(rain_dev_pct) / 100.0, 1.0)
    weather_anomaly_val = max(temp_dev, rain_dev)

    return SignalBundle(
        district=district,
        state=state,
        humidity_7d_avg=humidity_avg,
        rainfall_deviation_pct=rain_dev_pct,
        weather_anomaly=weather_anomaly_val,
        pest_risk=pest_risk_float,
        active_pest=pest_name,
        weather_anomaly_flag=abs(temp_anomaly) > 3.5 or abs(rain_dev_pct) > 50.0
    )

@app.get("/signals/weather", response_model=SignalBundle)
async def get_weather_signals(lat: float = Query(...), lon: float = Query(...)):
    """Primary weather endpoint: specific to latitude and longitude."""
    location_key = f"{round(lat, 2)},{round(lon, 2)}"
    if location_key in WEATHER_CACHE:
        c = WEATHER_CACHE[location_key]
        return SignalBundle(
            district=c["district"],
            state=c["state"],
            humidity_7d_avg=c["humidity_7d_avg"],
            rainfall_deviation_pct=c["rainfall_deviation_pct"],
            weather_anomaly=c["weather_anomaly"],
            pest_risk=c["pest_risk"],
            active_pest=c["active_pest"],
            weather_anomaly_flag=c["weather_anomaly_flag"]
        )

    # 1. Reverse Geocode for District/State context
    district, state = await get_district_from_coords(lat, lon)
    
    # 2. Fetch Signals and Baselines
    try:
        (hist_temp, hist_rain), (curr_temp, humidity_avg, rain_7d) = await asyncio.gather(
            get_historical_baselines(lat, lon),
            get_current_weather(lat, lon)
        )
    except Exception as e:
        print(f"Error fetching weather APIs: {e}")
        hist_temp, hist_rain = 30.0, 50.0
        curr_temp, humidity_avg, rain_7d = 32.0, 65.0, 10.0

    print("historical baselines" , hist_temp, hist_rain)
    pest_name, pest_risk = get_pest_risk(district)
    
    return build_signal_bundle(
        district=district,
        state=state,
        humidity_avg=humidity_avg,
        rain_7d=rain_7d,
        curr_temp=curr_temp,
        hist_temp=hist_temp,
        hist_rain=hist_rain,
        pest_name=pest_name,
        pest_risk=pest_risk
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
