import json
import os
import csv
import sys
import random
# Allow executing this file directly from anywhere in the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from shared.models import Farmer, Product, WhatsAppCampaign, FarmerProfile, SignalBundle, FarmerStage, FarmerContext, CropType

WEATHER_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "dataset", "weather_cache.csv"
)
GROWER_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "dataset", "grower_urgency_cache.csv"
)

def load_weather_cache() -> dict:
    cache = {}
    if os.path.exists(WEATHER_CACHE_PATH):
        with open(WEATHER_CACHE_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                loc_key = row.get("location_key")
                if loc_key:
                    pest_val = row.get("pest_risk") or row.get("pest_risk_level") or "low"
                    if pest_val in ["low", "medium", "high"]:
                        pest_risk_float = {"high": 0.8, "medium": 0.5, "low": 0.2}[pest_val]
                    else:
                        try:
                            pest_risk_float = float(pest_val)
                        except ValueError:
                            pest_risk_float = 0.2

                    raw_wa = row.get("weather_anomaly") 
                    try:
                        raw_wa_val = float(raw_wa) if raw_wa is not None else 0.0
                        if 0.0 <= raw_wa_val <= 1.0:
                            wa_val = raw_wa_val
                        else:
                            wa_val = min(abs(raw_wa_val) / 5.0, 1.0)
                    except ValueError:
                        wa_val = 0.2

                    cache[loc_key] = {
                        "district": row.get("district"),
                        "state": row.get("state"),
                        "humidity_7d_avg": float(row.get("humidity_7d_avg") or 0.0),
                        "rainfall_deviation_pct": float(row.get("rainfall_deviation_pct") or 0.0),
                        "weather_anomaly": wa_val,
                        "pest_risk": pest_risk_float,
                        "active_pest": row.get("active_pest") or "None",
                        "weather_anomaly_flag": str(row.get("weather_anomaly_flag")).lower() == "true",
                    }
    return cache

def load_grower_cache() -> dict:
    cache = {}
    if os.path.exists(GROWER_CACHE_PATH):
        with open(GROWER_CACHE_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                grower_id = row.get("grower_id")
                if grower_id:
                    cache[grower_id] = {
                        "urgency_score": float(row.get("urgency_score") or 0.0),
                        "recommended_channel": row.get("recommended_channel")
                    }
    return cache

def write_weather_cache(rows):
    file_exists = os.path.exists(WEATHER_CACHE_PATH)
    fieldnames = [
        "location_key", "district", "state", "humidity_7d_avg", 
        "rainfall_deviation_pct", "weather_anomaly", 
        "pest_risk", "active_pest", "weather_anomaly_flag"
    ]
    with open(WEATHER_CACHE_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

def write_grower_cache(rows):
    file_exists = os.path.exists(GROWER_CACHE_PATH)
    fieldnames = ["grower_id", "urgency_score", "recommended_channel"]
    with open(GROWER_CACHE_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

DEMO_FARMERS: list[dict] = [
    {
        "farmer_id": "GRW_00001",
        "name": "Grower GRW_00001",
        "state": "Uttar Pradesh",
        "district": "Kanpur Nagar",
        "tehsil": "Kanpur_Nagar_T124",
        "preferred_language": "Hindi",
        "crops": "wheat",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "device_type": "android",
        "connectivity": "4G",
        "grower_age": 42,
        "grower_farm_size": 1.33,
    },
    {
        "farmer_id": "GRW_00005",
        "name": "Rajan Kumar",
        "state": "Uttar Pradesh",
        "district": "Lucknow",
        "tehsil": "Lucknow_Rural",
        "preferred_language": "Hindi",
        "crops": "wheat",
        "latitude": 26.85,
        "longitude": 80.95,
        "device_type": "android",
        "connectivity": "4G",
        "grower_age": 38,
        "grower_farm_size": 2.1,
    },
    {
        "farmer_id": "GJ-014",
        "name": "Mayur",
        "state": "Gujarat",
        "district": "Anand",
        "tehsil": "Boriavi",
        "preferred_language": "Gujarati",
        "crops": "cotton",
        "latitude": 22.5645,
        "longitude": 72.9289,
        "device_type": "android",
        "connectivity": "4G",
        "grower_age": 34,
        "grower_farm_size": 1.8,
        "phone": "+919152155576",
    },
    {
        "farmer_id": "BR-001",
        "name": "Rajnish",
        "state": "Bihar",
        "district": "Patna",
        "tehsil": "Danapur",
        "preferred_language": "Bhojpuri",
        "crops": "rice",
        "latitude": 25.5941,
        "longitude": 85.1376,
        "device_type": "feature_phone",
        "connectivity": "2G",
        "grower_age": 45,
        "grower_farm_size": 1.2,
    },
    {
        "farmer_id": "TN-042",
        "name": "Rajan Kumar",
        "state": "Tamil Nadu",
        "district": "Thanjavur",
        "tehsil": "Papanasam",
        "preferred_language": "Tamil",
        "crops": "rice",
        "latitude": 10.787,
        "longitude": 79.1378,
        "device_type": "android",
        "connectivity": "4G",
        "grower_age": 50,
        "grower_farm_size": 2.5,
    },
]


def seed_demo_farmers(db: Session) -> int:
    """Seed a small demo set when dataset/growers.csv is not available."""
    db.query(Farmer).delete()
    farmers = []
    for i, row in enumerate(DEMO_FARMERS):
        fid = row["farmer_id"]
        phone = row.get("phone") or f"+91-9{i:09d}"
        farmers.append(
            Farmer(
                farmer_id=fid,
                name=row["name"],
                phone=phone,
                preferred_language=row["preferred_language"],
                state=row["state"],
                district=row["district"],
                tehsil=row["tehsil"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                grower_farm_size=row["grower_farm_size"],
                crops=row["crops"],
                device_type=row["device_type"],
                connectivity=row["connectivity"],
                whatsapp_enabled=row["device_type"] != "feature_phone",
                last_message_sent_at=None,
                messages_received_last_30d=0,
                messages_opened_last_30d=0,
                preferred_contact_time="morning",
                linked_retailer_id=f"RET-{200 + i:03d}",
                linked_retailer_name=f"{row['district']} Agro Center",
                urgency_score=0.5,
                recommended_channel="whatsapp",
                grower_age=row["grower_age"],
                gender="male",
                grower_crop_calendar=None,
                product_scan=False,
                product_name=None,
                product_scan_datetime=None,
                offline_campaign_attended=False,
                campaign_attendance_date=None,
            )
        )
    for f in farmers:
        db.add(f)
    db.commit()
    return len(farmers)


def seed_farmers(db: Session):
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset", "growers.csv")
    if not os.path.exists(csv_path):
        print(f"growers.csv not found at {csv_path}; using demo farmers ({len(DEMO_FARMERS)} rows).")
        return seed_demo_farmers(db)

    db.query(Farmer).delete()

    weather_cache = load_weather_cache()
    grower_cache = load_grower_cache()
    new_weather_rows = []
    new_grower_rows = []

    wa_counts = {}
    wa_csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset", "whatsapp_campaign.csv")
    if os.path.exists(wa_csv_path):
        with open(wa_csv_path, newline="", encoding="utf-8") as f_wa:
            reader = csv.DictReader(f_wa)
            for row in reader:
                g_id = row.get("grower_id", "").strip()
                if not g_id:
                    continue
                delivered = str(row.get("delivered_status")).lower() == 'true'
                opened = str(row.get("opened_status")).lower() == 'true'
                if g_id not in wa_counts:
                    wa_counts[g_id] = {"received": 0, "opened": 0}
                if delivered:
                    wa_counts[g_id]["received"] += 1
                if opened:
                    wa_counts[g_id]["opened"] += 1

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

    indian_names = [
        "Rajan Kumar", "Suresh Reddy", "Vijay Patil", "Amit Singh", "Ramesh Kumar",
        "Anil Sharma", "Sanjay Gupta", "Mahesh Babu", "Sunil Verma", "Ajay Meena",
        "Vikram Singh", "Pankaj Yadav", "Santosh Mane", "Ganesh Hegde", "Sandeep Chaudhary",
        "Manoj Tiwari", "Kishore Bhagat", "Harish Rao", "Pradeep Naik", "Nitin Gadkari",
        "Deepak Deshmukh", "Arun Jaitley", "Kapil Dev", "Sachin Kulkarni", "Virat Chauhan"
    ]
    farmers = []

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

            from urgency_scorer.scorer import compute_urgency
            import unittest.mock as mock
            import asyncio
            from weather_service import main as weather_main

            # Map Crop Type to valid CropType Enum
            crop_val = "wheat"
            for ct in CropType:
                if ct.value == crop:
                    crop_val = crop
                    break

            received_last_30d = wa_counts.get(grower_id, {}).get("received", 0)
            opened_last_30d = wa_counts.get(grower_id, {}).get("opened", 0)

            profile_obj = FarmerProfile(
                grower_id=grower_id,
                name=indian_names[i % len(indian_names)],
                grower_age=age,
                phone=phone,
                preferred_language=language,
                state=state,
                district=district,
                tehsil=tehsil,
                grower_farm_size=acres,
                crops=[crop_val],
                latitude=lat,
                longitude=lon,
                device_type=device_type,
                connectivity=connectivity,
                whatsapp_enabled=device_type != "feature_phone",
                last_message_sent_at=recent_campaign_date or None,
                messages_received_last_30d=received_last_30d,
                messages_opened_last_30d=opened_last_30d,
                preferred_contact_time=random.choice(["morning", "afternoon", "evening"]),
                linked_retailer_id=f"RET-{200 + i:03d}",
                linked_retailer_name=f"{district} Agro Center",
            )
            
            location_key = f"{round(lat, 2)},{round(lon, 2)}"
            
            # Weather signals logic
            if location_key in weather_cache:
                cached_w = weather_cache[location_key]
                signals_obj = SignalBundle(
                    district=district,
                    state=state,
                    humidity_7d_avg=cached_w["humidity_7d_avg"],
                    rainfall_deviation_pct=cached_w["rainfall_deviation_pct"],
                    weather_anomaly=cached_w["weather_anomaly"],
                    pest_risk=cached_w["pest_risk"],
                    active_pest=cached_w["active_pest"],
                    weather_anomaly_flag=cached_w["weather_anomaly_flag"]
                )
            else:
                from weather_service.main import (
                    get_historical_baselines, get_current_weather, build_signal_bundle, get_pest_risk
                )
                async def fetch_weather():
                    return await asyncio.gather(
                        get_historical_baselines(lat, lon),
                        get_current_weather(lat, lon)
                    )
                try:
                    (hist_temp, hist_rain), (curr_temp, humidity_avg, rain_7d) = asyncio.run(fetch_weather())
                except Exception as e:
                    print(f"Error fetching weather APIs for {location_key}: {e}")
                    hist_temp, hist_rain = 30.0, 50.0
                    curr_temp, humidity_avg, rain_7d = 32.0, 65.0, 10.0

                pest_name, pest_risk = get_pest_risk(district)
                signals_obj = build_signal_bundle(
                    district=district,
                    state=state,
                    humidity_avg=humidity_avg,
                    rain_7d=rain_7d,
                    curr_temp=curr_temp,
                    hist_temp=hist_temp,
                    hist_rain=hist_rain,
                    pest_name=pest_name,
                    pest_risk=pest_risk
                )
                weather_cache[location_key] = {
                    "district": district,
                    "state": state,
                    "humidity_7d_avg": signals_obj.humidity_7d_avg,
                    "rainfall_deviation_pct": signals_obj.rainfall_deviation_pct,
                    "weather_anomaly": signals_obj.weather_anomaly,
                    "pest_risk": signals_obj.pest_risk,
                    "active_pest": signals_obj.active_pest,
                    "weather_anomaly_flag": signals_obj.weather_anomaly_flag
                }
                new_weather_rows.append({
                    "location_key": location_key,
                    "district": district,
                    "state": state,
                    "humidity_7d_avg": signals_obj.humidity_7d_avg,
                    "rainfall_deviation_pct": signals_obj.rainfall_deviation_pct,
                    "weather_anomaly": signals_obj.weather_anomaly,
                    "pest_risk": signals_obj.pest_risk,
                    "active_pest": signals_obj.active_pest,
                    "weather_anomaly_flag": str(signals_obj.weather_anomaly_flag)
                })

            # Urgency logic
            if grower_id in grower_cache:
                cached_g = grower_cache[grower_id]
                urgency_score_val = cached_g["urgency_score"]
                recommended_channel_val = cached_g["recommended_channel"]
            else:
                stage_obj = FarmerStage(
                    confirmed_stage="vegetative",
                    days_in_stage=0,
                    crop_vulnerability=0.5,
                    days_to_next_stage=30
                )
                
                urgency_ctx = FarmerContext(
                    profile=profile_obj,
                    signals=signals_obj,
                    crop_stage=stage_obj,
                    assembled_at="2026-04-05T00:00:00"
                )

                urgency_score_val = 0.0
                recommended_channel_val = None

                try:
                    urgency_res = compute_urgency(urgency_ctx)
                    urgency_score_val = urgency_res.urgency_score
                    recommended_channel_val = urgency_res.recommended_channel.value
                except Exception as exc:
                    print(f"Error computing urgency for {grower_id} during seeding: {exc}")

                grower_cache[grower_id] = {
                    "urgency_score": urgency_score_val,
                    "recommended_channel": recommended_channel_val
                }
                new_grower_rows.append({
                    "grower_id": grower_id,
                    "urgency_score": urgency_score_val,
                    "recommended_channel": recommended_channel_val
                })

            if len(new_weather_rows) >= 50:
                write_weather_cache(new_weather_rows)
                new_weather_rows.clear()

            if len(new_grower_rows) >= 50:
                write_grower_cache(new_grower_rows)
                new_grower_rows.clear()

            farmers.append(Farmer(
                grower_id=grower_id,
                name=indian_names[i % len(indian_names)],
                phone=phone,
                preferred_language=language,
                state=state,
                district=district,
                latitude=lat,
                longitude=lon,
                grower_farm_size=acres,
                crops=crop,
                device_type=device_type,
                connectivity=connectivity,
                whatsapp_enabled=device_type != "feature_phone",
                last_message_sent_at=recent_campaign_date or None,
                messages_received_last_30d=received_last_30d,
                messages_opened_last_30d=opened_last_30d,
                preferred_contact_time=random.choice(["morning", "afternoon", "evening"]),
                linked_retailer_id=f"RET-{200 + i:03d}",
                linked_retailer_name=f"{district} Agro Center",
                urgency_score=urgency_score_val,
                recommended_channel=recommended_channel_val,
                tehsil=tehsil,
                grower_age=age,
                gender=row.get("gender"),
                grower_crop_calendar=row.get("grower_crop_calendar"),
                product_scan=str(row.get("product_scan")).lower() == 'true',
                product_name=row.get("product_name"),
                product_scan_datetime=row.get("product_scan_datetime"),
                offline_campaign_attended=str(row.get("offline_campaign_attended")).lower() == 'true',
                campaign_attendance_date=row.get("campaign_attendance_date")
            ))
            
    if new_weather_rows:
        write_weather_cache(new_weather_rows)
    if new_grower_rows:
        write_grower_cache(new_grower_rows)

    for f in farmers:
        db.add(f)
    db.commit()
    return len(farmers)

def seed_products(db: Session):
    db.query(Product).delete()
    
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "product-catalog", "canonical_products.json")
    
    product_objects = []
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
            for item in data:
                product_objects.append(Product(
                    name=item.get("name"),
                    type=item.get("type"),
                    active_ingredients=item.get("active_ingredients"),
                    description=item.get("description"),
                    target_crop=item.get("target_crop"),
                    target_pest=item.get("target_pest"),
                    effective_stages=item.get("effective_stages"),
                    treatment_intent=item.get("treatment_intent"),
                    efficacy_rating=item.get("efficacy_rating"),
                    price_tier=item.get("price_tier"),
                    application_mode=item.get("application_mode"),
                    systemic=item.get("systemic"),
                    rain_sensitive_hours=item.get("rain_sensitive_hours"),
                    moa_group=item.get("moa_group"),
                    moa_class=item.get("moa_class"),
                    resistance_management=item.get("resistance_management"),
                    epa_number=item.get("epa_number"),
                    logo_url=item.get("logo_url"),
                    product_url=item.get("product_url"),
                    directions=item.get("directions")
                ))
                
        db.bulk_save_objects(product_objects)
        db.commit()
    else:
        print(f"Warning: {file_path} not found.")
        
    return len(product_objects)

if __name__ == "__main__":
    from app.database import init_db, SessionLocal
    print("Initializing database...")
    init_db()
    db = SessionLocal()
    try:
        print("Seeding farmers...")
        farmers_count = seed_farmers(db)
        print(f"Successfully seeded {farmers_count} farmers.")
        
        print("Seeding products...")
        products_count = seed_products(db)
        print(f"Successfully seeded {products_count} products.")
        
        print("Seeding WhatsApp campaigns...")
        db.query(WhatsAppCampaign).delete()
        
        wa_csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset", "whatsapp_campaign.csv")
        wa_campaigns = []
        if os.path.exists(wa_csv_path):
            with open(wa_csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    wa_campaigns.append(WhatsAppCampaign(
                        id=row.get("id"),
                        campaign_product=row.get("campaign_product"),
                        campaign_crop=row.get("campaign_crop"),
                        grower_id=row.get("grower_id"),
                        message_sent_date=row.get("message_sent_date"),
                        delivered_status=str(row.get("delivered_status")).lower() == 'true',
                        opened_status=str(row.get("opened_status")).lower() == 'true',
                        clicked_status=str(row.get("clicked_status")).lower() == 'true'
                    ))
            db.bulk_save_objects(wa_campaigns)
            db.commit()
            print(f"Successfully seeded {len(wa_campaigns)} WhatsApp campaigns.")
        else:
            print(f"Warning: {wa_csv_path} not found.")
            
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()
