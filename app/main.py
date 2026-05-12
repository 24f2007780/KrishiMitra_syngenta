from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, database, seeder

app = FastAPI(title="Syngenta Master Database API")

@app.on_event("startup")
def startup():
    database.init_db()

# Farmer Endpoints
@app.get("/farmer/{farmer_id}", response_model=models.FarmerProfile)
def get_farmer(farmer_id: str, db: Session = Depends(database.get_db)):
    farmer = db.query(models.Farmer).filter(models.Farmer.farmer_id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer

@app.get("/farmers", response_model=List[models.FarmerProfile])
def list_farmers(
    state: Optional[str] = Query(None),
    crop: Optional[str] = Query(None),
    urgency_min: Optional[float] = Query(None),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Farmer)
    if state:
        query = query.filter(models.Farmer.state == state)
    if crop:
        query = query.filter(models.Farmer.crops.contains(crop.lower()))
    if urgency_min is not None:
        query = query.filter(models.Farmer.urgency_score >= urgency_min)
    return query.all()

@app.post("/farmers/seed")
def seed_farmers(db: Session = Depends(database.get_db)):
    seeder.seed_farmers(db)
    return {"message": "Successfully seeded 25 farmers with detailed profiles."}

# Product Endpoints
@app.get("/products", response_model=List[models.ProductProfile])
def list_products(
    crop: Optional[str] = Query(None),
    pest: Optional[str] = Query(None),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Product)
    if crop:
        query = query.filter(models.Product.target_crop.contains(crop.lower()))
    if pest:
        query = query.filter(models.Product.target_pest.contains(pest.lower()))
    return query.all()

@app.post("/seed-all")
def seed_all(db: Session = Depends(database.get_db)):
    # Re-init DB schema to handle primary key change
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    
    seeder.seed_farmers(db)
    count = seeder.seed_products(db)
    return {"message": f"Master database seeded: 25 detailed farmers and {count} products."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
