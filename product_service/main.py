from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app import database, seeder
from shared import models

app = FastAPI(title="Syngenta Product Catalog (M2)")

@app.on_event("startup")
def startup():
    database.init_db()

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


@app.get("/health")
def health():
    return {"status": "ok", "module": "M2"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
