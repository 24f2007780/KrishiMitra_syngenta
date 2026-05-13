import httpx
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from shared import models

app = FastAPI(title="Syngenta Product Ranker (M8)")

M2_URL = "http://localhost:8002"

@app.post("/rank")
async def rank_products(body: Dict):
    # Parsing input manually to handle potential schema variations
    context_dict = body.get("context")
    urgency_score = body.get("urgency_score", 0.0)
    
    if not context_dict:
        raise HTTPException(status_code=400, detail="Missing context in request body")
    
    try:
        context = models.FarmerContext(**context_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid context format: {e}")

    crop = context.profile.crops[0] if context.profile.crops else "general"
    pest = context.signals.active_pest or "general"
    stage = context.crop_stage.confirmed_stage.lower()

    # 1. Fetch candidate products from M2
    async with httpx.AsyncClient() as client:
        try:
            # We fetch products matching the crop and optionally the pest
            res = await client.get(f"{M2_URL}/products", params={"crop": crop})
            res.raise_for_status()
            candidates = [models.ProductProfile(**p) for p in res.json()]
        except Exception as e:
            print(f"ERROR fetching products from M2: {e}")
            candidates = []

    # 2. Rule-based Ranking Engine
    scored_products = []
    for product in candidates:
        score = 0.0
        reasons = []

        # A) Pest match (Primary)
        # Check if the exact pest is in target_pest
        if pest.lower() in (product.target_pest or "").lower():
            score += 2.0
            reasons.append(f"Direct match for {pest}")
        elif pest.lower() in (product.description or "").lower():
            score += 1.0
            reasons.append(f"Effective against {pest} symptoms")

        # B) Stage Window Match
        # Logic: Seeds for sowing/seed_treatment, chemicals for vegetative/flowering
        if stage in ["sowing", "seed_treatment"]:
            if product.type == "seed":
                score += 1.5
                reasons.append(f"Ideal for your current {stage} stage")
            elif "seed treatment" in (product.description or "").lower():
                score += 1.5
                reasons.append(f"Specifically formulated for seed protection")
        elif stage in ["vegetative", "flowering"]:
            if product.type in ["fungicide", "insecticide"]:
                score += 1.0
                reasons.append(f"Protects crop during critical {stage} growth")
        
        # C) Urgency Alignment
        if urgency_score > 0.7 and product.type in ["fungicide", "insecticide"]:
            score += 0.5
            reasons.append("Fast-acting solution for high-risk conditions")

        if score > 0:
            scored_products.append({
                "name": product.name,
                "score": score,
                "reason": reasons[0] if reasons else "Good match for your crop"
            })

    # 3. Sort and Return Top 2
    scored_products.sort(key=lambda x: x["score"], reverse=True)
    top_2 = scored_products[:2]

    # 4. Fallback if no match
    if not top_2:
        # Get any products for this crop as generic fallback
        if candidates:
            top_2 = [{"name": candidates[0].name, "reason": f"Highly recommended for {crop} farmers in your region"}]
        else:
            top_2 = [{"name": "Generic Crop Protection", "reason": "Universal protection for your crop type"}]

    return {
        "top_products": [p["name"] for p in top_2],
        "match_reasons": [p["reason"] for p in top_2]
    }

@app.get("/health")
def health():
    return {"status": "ok", "module": "M8"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
