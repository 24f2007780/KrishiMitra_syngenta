import asyncio
import httpx
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException
from shared import models

app = FastAPI(title="Syngenta Context Assembler (M6)")

# Service URLs
M1_URL = "http://localhost:8001"
M4_URL = "http://localhost:8004"
M5_URL = "http://localhost:8005"

# Mock/Fallback SignalBundle if M4 is down
MOCK_SIGNALS = models.SignalBundle(
    humidity_7d_avg=65.0,
    rainfall_deviation_pct=0.0,
    weather_anomaly=0.0,
    pest_risk=0.2,
    active_pest="None",
    weather_anomaly_flag=False
)

async def fetch_farmer_context(grower_id: str, client: httpx.AsyncClient) -> models.FarmerContext:
    # 1. Fetch Farmer Profile (M1)
    try:
        profile_res = await client.get(f"{M1_URL}/farmer/{grower_id}")
        profile_res.raise_for_status()
        profile = models.FarmerProfile(**profile_res.json())
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Farmer {grower_id} not found")
        raise HTTPException(status_code=500, detail=f"M1 Service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to M1: {e}")

    # 2. Fetch Weather Signals (M4) - With Fallback
    try:
        weather_res = await client.get(
            f"{M4_URL}/signals/weather",
            params={"lat": profile.latitude, "lon": profile.longitude},
            timeout=15.0
        )
        weather_res.raise_for_status()
        signals = models.SignalBundle(**weather_res.json())
    except Exception as e:
        print(f"WARNING: M4 Service error for farmer {grower_id}, using mock signals: {e}")
        signals = MOCK_SIGNALS
        signals.district = profile.district
        signals.state = profile.state

    # 3. Fetch Crop Stage (M5)
    try:
        # Use first crop in farmer's crops list
        crop = profile.crops[0] if profile.crops else "rice"
        calendar_res = await client.get(
            f"{M5_URL}/calendar",
            params={"state": profile.state, "crop": crop},
            timeout=15.0
        )
        calendar_res.raise_for_status()
        cal_data = calendar_res.json()
        
        crop_stage = models.FarmerStage(
            confirmed_stage=cal_data["stage"],
            days_in_stage=0, # Defaulting as it's not provided by M5
            crop_vulnerability=cal_data["crop_vulnerability"],
            days_to_next_stage=cal_data["days_to_next"]
        )
    except Exception as e:
        print(f"WARNING: M5 Service error for farmer {grower_id}: {e}")
        # Provide a safe default stage if M5 fails
        crop_stage = models.FarmerStage(
            confirmed_stage="vegetative",
            days_in_stage=0,
            crop_vulnerability=0.2,
            days_to_next_stage=30
        )

    return models.FarmerContext(
        profile=profile,
        signals=signals,
        crop_stage=crop_stage,
        assembled_at=datetime.now().isoformat()
    )

@app.get("/context/{grower_id}", response_model=models.FarmerContext)
async def get_farmer_context(grower_id: str):
    async with httpx.AsyncClient() as client:
        return await fetch_farmer_context(grower_id, client)

@app.post("/context/batch", response_model=List[models.FarmerContext])
async def batch_context(grower_ids: List[str]):
    async with httpx.AsyncClient() as client:
        tasks = [fetch_farmer_context(fid, client) for fid in grower_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors and return successful contexts
        contexts = []
        for res in results:
            if isinstance(res, models.FarmerContext):
                contexts.append(res)
            else:
                print(f"ERROR assembling context: {res}")
        
        return contexts

@app.get("/health")
def health():
    return {"status": "ok", "module": "M6"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
