import json
import os
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
from shared import models

app = FastAPI(title="Syngenta Crop Calendar (M5)")

# ICAR-based hardcoded calendars
KHARIF_CYCLE = {
    6: ("sowing", "high", 30), 7: ("vegetative", "medium", 45), 8: ("vegetative", "medium", 30),
    9: ("flowering", "high", 30), 10: ("harvest", "low", 60), 11: ("harvest", "low", 30),
    12: ("fallow", "low", 30), 1: ("fallow", "low", 30), 2: ("fallow", "low", 30),
    3: ("fallow", "low", 30), 4: ("fallow", "low", 30), 5: ("seed_treatment", "low", 15),
}

RABI_CYCLE = {
    10: ("sowing", "high", 30), 11: ("vegetative", "medium", 45), 12: ("vegetative", "medium", 45),
    1: ("flowering", "high", 30), 2: ("flowering", "high", 30), 3: ("harvest", "low", 30),
    4: ("fallow", "low", 30), 5: ("fallow", "low", 30), 6: ("fallow", "low", 30),
    7: ("fallow", "low", 30), 8: ("fallow", "low", 30), 9: ("fallow", "low", 15),
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
        
        crop_norm = crop.lower().strip()
        synonyms = {"rice": "paddy", "paddy": "rice", "soybean": "soyabean", "soyabean": "soybean", "urad": "blackgram", "moong": "greengram", "tur": "redgram"}
        
        # Gather matching crop data (exact + synonym + fuzzy)
        targets = {crop_norm}
        if crop_norm in synonyms: targets.add(synonyms[crop_norm])
        
        results = []
        for key, crop_data in data.items():
            if any(t in key.lower() or key.lower() in t for t in targets):
                recs = crop_data.get("common_instructions", crop_data) if isinstance(crop_data, dict) else crop_data
                for item in recs:
                    item_stage = item.get("stage", "").lower()
                    if item_stage == stage.lower() or item_stage == "all_stages" or stage.lower() in item_stage or item_stage in stage.lower():
                        content = item.get("content", "")
                        if content and content not in results:
                            results.append(content)
        return results
    except Exception as e:
        print(f"Error loading recommendations: {e}")
        return []

@app.get("/")
def read_root():
    return {"message": "Welcome to Syngenta Crop Calendar API"}

@app.get("/calendar", response_model=models.CropStageInfo)
async def get_crop_calendar(
    state: str = Query(..., examples=["Tamil Nadu"]),
    crop: str = Query(..., examples=["rice"]),
    month: Optional[int] = Query(None)
):
    month = month or datetime.now().month
    
    # Fuzzy state match
    state_match = next((s for s in STATE_FILES if state.lower() in s.lower() or s.lower() in state.lower()), None)
    if not state_match: raise HTTPException(status_code=404, detail=f"State '{state}' not supported")
    state = state_match

    crop_norm = crop.lower().strip()
    # Fuzzy crop/cycle match
    all_crops = KHARIF_CROPS + RABI_CROPS
    crop_match = next((c for c in all_crops if crop_norm in c or c in crop_norm), None)
    if not crop_match:
        raise HTTPException(status_code=404, detail=f"Crop '{crop}' not supported")
    
    cycle = KHARIF_CYCLE if crop_match in KHARIF_CROPS else RABI_CYCLE
    
    stage_data = cycle.get(month)
    if not stage_data: raise HTTPException(status_code=404, detail="Calendar data not found for this month")

    stage, vulnerability, days_to_next = stage_data
    recommendations = load_recommendations(state, crop, stage)

    # Fetch Market Data
    market_data = {"msp": None, "price": None, "arrival": None}
    try:
        market_syns = {"rice": "paddy", "blackgram": "urad", "greengram": "moong", "redgram": "arhar", "soybean": "soyabean"}
        lookup_crop = market_syns.get(crop_norm, crop_norm)
        async with httpx.AsyncClient(timeout=3.0) as client:
            m_res = await client.get(f"http://localhost:8000/commodity/{lookup_crop}")
            if m_res.status_code == 200:
                data_list = m_res.json().get("data", [])
                if data_list:
                    market_data = {
                        "msp": data_list[0].get("msp_rs_quintal"),
                        "price": data_list[0].get("today_price_rs_quintal"),
                        "arrival": data_list[0].get("today_arrival_metric_tonnes")
                    }
    except Exception as e:
        print(f"Market fetch failed for {crop_norm}: {e}")

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
