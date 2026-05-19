import json
from app.database import SessionLocal
from shared.models import Product

db = SessionLocal()
products = db.query(Product).all()

out = []
for p in products:
    d = {
        "id": p.id,
        "name": p.name,
        "type": p.type,
        "active_ingredients": p.active_ingredients,
        "description": p.description,
        "target_crop": p.target_crop,
        "target_pest": p.target_pest,
        "effective_stages": p.effective_stages,
        "treatment_intent": p.treatment_intent,
        "efficacy_rating": p.efficacy_rating,
        "price_tier": p.price_tier,
        "application_mode": p.application_mode,
        "systemic": p.systemic,
        "rain_sensitive_hours": p.rain_sensitive_hours,
        "moa_group": p.moa_group,
        "moa_class": p.moa_class,
        "resistance_management": p.resistance_management,
        "epa_number": p.epa_number,
        "logo_url": p.logo_url,
        "product_url": p.product_url,
        "directions": p.directions if hasattr(p, 'directions') else None
    }
    out.append(d)

with open('product-catalog/canonical_products.json', 'w') as f:
    json.dump(out, f, indent=4)
