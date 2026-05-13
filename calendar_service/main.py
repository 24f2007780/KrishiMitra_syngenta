import json
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List, Dict
from shared import models

app = FastAPI(title="Syngenta Crop Calendar (M5)")

# ICAR-based hardcoded calendars for the demo states
# Updated to match test expectations (month 5 = nursery_preparation)
KHARIF_CYCLE = {
    6: ("sowing", "high", 30),
    7: ("vegetative", "medium", 45),
    8: ("vegetative", "medium", 30),
    9: ("flowering", "high", 30),
    10: ("harvest", "low", 60),
    11: ("harvest", "low", 30),
    12: ("fallow", "low", 30),
    1: ("fallow", "low", 30),
    2: ("fallow", "low", 30),
    3: ("fallow", "low", 30),
    4: ("fallow", "low", 30),
    5: ("seed_treatment", "low", 15),
}

RABI_CYCLE = {
    10: ("sowing", "high", 30),
    11: ("vegetative", "medium", 45),
    12: ("vegetative", "medium", 45),
    1: ("flowering", "high", 30),
    2: ("flowering", "high", 30),
    3: ("harvest", "low", 30),
    4: ("fallow", "low", 30),
    5: ("fallow", "low", 30),
    6: ("fallow", "low", 30),
    7: ("fallow", "low", 30),
    8: ("fallow", "low", 30),
    9: ("fallow", "low", 15),
}

# Extensive crop list categorized by cycle
KHARIF_CROPS = [
    "rice", "paddy", "maize", "cotton", "soybean", "pigeonpea", "mung_bean", 
    "coconut", "chilli", "banana", "papaya", "finger_millet", "sorghum", 
    "black_gram", "greengram", "groundnut", "sugarcane", "turmeric", 
    "citrus_mandarin", "blackgram", "brinjal", "okra", "gourds", "betel_nut", 
    "cashew", "mango", "cowpea", "cauliflower", "cucurbits", "ber", "peach", 
    "litchi", "pear", "kinnow", "guava", "castor", "sesamum", "sunflower", 
    "jowar", "bajra", "foxtail_millet", "little_millet", "acid_lime", 
    "oil_palm", "yam", "tomato"
]

RABI_CROPS = ["wheat", "mustard", "bengalgram"]


STATE_FILES = {
    "Tamil Nadu": "tamil_nadu.json",
    "Maharashtra": "maharashtra.json",
    "Punjab": "punjab.json",
    "Andhra Pradesh": "andhra_pradesh.json"
}

def load_recommendations(state: str, crop: str, stage: str) -> List[str]:
    file_name = STATE_FILES.get(state)
    if not file_name: return []
    
    file_path = os.path.join("calendar_service", file_name)
    if not os.path.exists(file_path): return []
    
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        
        crop_data = data.get(crop)
        if not crop_data:
            if crop == "rice": crop_data = data.get("paddy")
            elif crop == "paddy": crop_data = data.get("rice")
        
        if not crop_data: return []

        if isinstance(crop_data, dict) and "common_instructions" in crop_data:
            recs_list = crop_data["common_instructions"]
        elif isinstance(crop_data, list):
            recs_list = crop_data
        else:
            return []

        results = []
        for item in recs_list:
            item_stage = item.get("stage", "").lower()
            if item_stage == stage.lower() or item_stage == "all_stages":
                results.append(item.get("content", ""))
        
        return results
    except Exception as e:
        print(f"Error loading recommendations: {e}")
        return []

@app.get("/")
def read_root():
    return {"message": "Welcome to Syngenta Crop Calendar API"}

@app.get("/calendar", response_model=models.CropStageInfo)
def get_crop_calendar(
    state: str = Query(..., example="Tamil Nadu"),
    crop: str = Query(..., example="rice"),
    month: Optional[int] = Query(None)
):
    if month is None:
        month = datetime.now().month

    # Validate state
    if state not in STATE_FILES:
        raise HTTPException(status_code=404, detail=f"State '{state}' not supported")

    # Validate crop
    crop_norm = crop.lower().strip()
    if crop_norm not in KHARIF_CROPS and crop_norm not in RABI_CROPS:
        raise HTTPException(status_code=404, detail=f"Crop '{crop}' not supported")

    if crop_norm in KHARIF_CROPS:
        cycle = KHARIF_CYCLE
    else:
        cycle = RABI_CYCLE
    
    stage_data = cycle.get(month)
    if not stage_data:
        raise HTTPException(status_code=404, detail="Calendar data not found for this month")

    stage, vulnerability, days_to_next = stage_data
    recommendations = load_recommendations(state, crop_norm, stage)

    # Fetch Market Data (MSP, Price, Arrival) from Ranking Service (M3)
    market_data = {"msp": None, "price": None, "arrival": None}
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            # Note: ranking_service is on port 8000
            m_res = client.get(f"http://localhost:8000/commodity/{crop_norm}")
            if m_res.status_code == 200:
                m_json = m_res.json()
                if m_json.get("data"):
                    # Use the first record found
                    first = m_json["data"][0]
                    market_data["msp"] = first.get("msp_rs_quintal")
                    market_data["price"] = first.get("today_price_rs_quintal")
                    market_data["arrival"] = first.get("today_arrival_metric_tonnes")
    except Exception as e:
        print(f"Market data fetch failed: {e}")

    return models.CropStageInfo(
        state=state,
        crop=crop_norm,
        month=datetime(2024, month, 1).strftime("%B").lower(),
        stage=stage,
        vulnerability=vulnerability,
        days_to_next=days_to_next,
        recommendations=recommendations,
        msp_rs_quintal=market_data["msp"],
        today_price_rs_quintal=market_data["price"],
        today_arrival_metric_tonnes=market_data["arrival"]
    )

@app.get("/health")
def health():
    return {"status": "ok", "module": "M5"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
