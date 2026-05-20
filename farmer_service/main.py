from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app import database, seeder
from shared import models

app = FastAPI(title="Syngenta Farmer DB (M1)")

@app.on_event("startup")
def startup():
    database.init_db()
    db = database.SessionLocal()
    try:
        if db.query(models.Farmer).count() == 0:
            seeder.seed_farmers(db)
    finally:
        db.close()

def db_farmer_to_profile(farmer: models.Farmer) -> models.FarmerProfile:
    crops_list = [c.strip() for c in farmer.crops.split(",")] if farmer.crops else []
    return models.FarmerProfile(
        grower_id=farmer.grower_id,
        name=farmer.name,
        grower_age=farmer.grower_age,
        phone=farmer.phone,
        preferred_language=farmer.preferred_language,
        state=farmer.state,
        district=farmer.district,
        tehsil=farmer.tehsil,
        grower_farm_size=farmer.grower_farm_size,
        crops=crops_list,
        latitude=farmer.latitude,
        longitude=farmer.longitude,
        device_type=farmer.device_type,
        connectivity=farmer.connectivity,
        whatsapp_enabled=farmer.whatsapp_enabled,
        last_message_sent_at=farmer.last_message_sent_at,
        messages_received_last_30d=farmer.messages_received_last_30d,
        messages_opened_last_30d=farmer.messages_opened_last_30d,
        preferred_contact_time=farmer.preferred_contact_time,
        linked_retailer_id=farmer.linked_retailer_id,
        linked_retailer_name=farmer.linked_retailer_name,
        urgency_score=farmer.urgency_score,
        recommended_channel=farmer.recommended_channel
    )

@app.get("/farmer/{grower_id}", response_model=models.FarmerProfile)
def get_farmer(grower_id: str, db: Session = Depends(database.get_db)):
    farmer = db.query(models.Farmer).filter(models.Farmer.grower_id == grower_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return db_farmer_to_profile(farmer)

@app.get("/farmers", response_model=List[models.FarmerProfile])
def list_farmers(
    state: Optional[str] = Query(None),
    crop: Optional[str] = Query(None),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Farmer)
    if state:
        query = query.filter(models.Farmer.state == state)
    if crop:
        query = query.filter(models.Farmer.crops.contains(crop.lower()))
    
    farmers = query.all()
    return [db_farmer_to_profile(f) for f in farmers]

@app.post("/farmers/seed")
def seed_farmers_endpoint(
    force: bool = Query(False, description="Re-seed even if farmers already exist"),
    db: Session = Depends(database.get_db),
):
    existing = db.query(models.Farmer).count()
    if existing > 0 and not force:
        return {
            "message": f"Already seeded ({existing} farmers). Pass ?force=true to replace.",
            "count": existing,
            "skipped": True,
        }
    try:
        count = seeder.seed_farmers(db)
        return {
            "message": f"Successfully seeded {count} farmers.",
            "count": count,
            "skipped": False,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seed failed: {e}") from e

@app.get("/health")
def health():
    return {"status": "ok", "module": "M1"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
