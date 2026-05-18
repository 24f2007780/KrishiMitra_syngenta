import json
import os
import csv
from sqlalchemy.orm import Session
from shared.models import Farmer, Product

def seed_farmers(db: Session):
    db.query(Farmer).delete()

    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "syngenta_data", "growers.csv")
    
    default_geo = {
        "Rajasthan": (27.0238, 74.2179),
        "Uttar Pradesh": (26.8467, 80.9462),
        "Punjab": (31.1471, 75.3412),
        "Maharashtra": (19.7515, 75.7139),
        "Haryana": (29.0588, 76.0856),
        "Gujarat": (22.2587, 71.1924),
        "Madhya Pradesh": (23.4733, 77.9479),
        "Karnataka": (15.3173, 75.7139),
        "Bihar": (25.0961, 85.3131),
        "West Bengal": (22.9868, 87.8550),
    }

    def map_device(raw: str) -> str:
        val = (raw or "").strip().lower()
        if val == "keypad":
            return "feature_phone"
        if val == "smartphone":
            return "android"
        return "feature_phone"

    def map_connectivity(raw: str) -> str:
        val = (raw or "").strip().lower()
        if val == "keypad":
            return "2G"
        if val == "smartphone":
            return "4G"
        return "3G"

    farmers = []
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"growers.csv not found at {csv_path}")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            state = row.get("state", "").strip() or "Unknown"
            district = row.get("district", "").strip() or "Unknown"
            tehsil = row.get("tehsil", "").strip()
            language = row.get("language", "").strip() or "Hindi"
            device_type = map_device(row.get("device_type", ""))
            connectivity = map_connectivity(row.get("device_type", ""))
            age = int(row.get("grower_age") or 35)
            acres = float(row.get("grower_farm_size") or 1.0)
            crop = "general"
            if row.get("grower_crop_calendar"):
                try:
                    crop = (json.loads(row["grower_crop_calendar"]).get("crop") or "general").lower()
                except (json.JSONDecodeError, TypeError):
                    crop = "general"

            recent_campaign_date = row.get("campaign_attendance_date", "").strip()
            lat_base, lon_base = default_geo.get(state, (22.9734, 78.6569))
            lat = round(lat_base, 4)
            lon = round(lon_base, 4)
            grower_id = (row.get("grower_id") or f"GRW_{i + 1:05d}").strip()
            phone = f"+91-9{i:09d}"

            farmers.append(Farmer(
                farmer_id=grower_id,
                name=f"Grower {grower_id}",
                age=age,
                phone=phone,
                preferred_language=language,
                state=state,
                district=district,
                village=tehsil or district,
                latitude=lat,
                longitude=lon,
                acres=acres,
                crops=crop,
                device_type=device_type,
                connectivity=connectivity,
                whatsapp_enabled=device_type != "feature_phone",
                last_message_sent_at=recent_campaign_date or None,
                messages_received_last_30d=0,
                messages_opened_last_30d=0,
                preferred_contact_time="morning",
                linked_retailer_id=f"RET-{200 + i:03d}",
                linked_retailer_name=f"{district} Agro Center",
                urgency_score=0.0
            ))
            
    for f in farmers:
        db.add(f)
    db.commit()
    return len(farmers)

def seed_products(db: Session):
    db.query(Product).delete()
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "product-catalog")
    files = [
        ("fungicides-productlist.json", "fungicide"),
        ("insectides-productlist.json", "insecticide"),
        ("herbicides-productslist.json", "herbicide"),
        ("seed-productslist.json", "seed")
    ]
    product_objects = []
    for filename, p_type in files:
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                for item in data:
                    desc = item.get("description", "").lower()
                    found_crops = [c for c in ["rice", "cotton", "wheat", "soybean", "corn"] if c in desc]
                    found_pests = [p for p in ["blast", "blight", "rust", "bollworm", "aphid"] if p in desc]
                    product_objects.append(Product(
                        name=item.get("name"),
                        type=p_type,
                        active_ingredients=item.get("active_ingredients"),
                        description=item.get("description"),
                        target_crop=", ".join(found_crops) if found_crops else "general",
                        target_pest=", ".join(found_pests) if found_pests else "general"
                    ))
    db.bulk_save_objects(product_objects)
    db.commit()
    return len(product_objects)
