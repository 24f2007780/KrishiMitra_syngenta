from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app import database, seeder
from shared import models

app = FastAPI(title="Syngenta Farmer DB (M1)")

@app.on_event("startup")
def startup():
    database.init_db()

def db_farmer_to_profile(farmer: models.Farmer) -> models.FarmerProfile:
    crops_list = [c.strip() for c in farmer.crops.split(",")] if farmer.crops else []
    return models.FarmerProfile(
        farmer_id=farmer.farmer_id,
        name=farmer.name,
        age=farmer.age,
        phone=farmer.phone,
        preferred_language=farmer.preferred_language,
        state=farmer.state,
        district=farmer.district,
        village=farmer.village,
        acres=farmer.acres,
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
        linked_retailer_name=farmer.linked_retailer_name
    )

@app.get("/farmer/{farmer_id}", response_model=models.FarmerProfile)
def get_farmer(farmer_id: str, db: Session = Depends(database.get_db)):
    farmer = db.query(models.Farmer).filter(models.Farmer.farmer_id == farmer_id).first()
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
def seed_farmers(db: Session = Depends(database.get_db)):
    count = seeder.seed_farmers(db)
    return {"message": f"Successfully seeded {count} farmers."}

@app.get("/health")
def health():
    return {"status": "ok", "module": "M1"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
