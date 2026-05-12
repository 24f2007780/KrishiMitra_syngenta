import json
import random
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from shared.models import Farmer, Product

def seed_farmers(db: Session):
    db.query(Farmer).delete()
    
    # 25 Realistic Indian names
    indian_names = [
        "Rajan Kumar", "Suresh Reddy", "Vijay Patil", "Amit Singh", "Ramesh Kumar",
        "Anil Sharma", "Sanjay Gupta", "Mahesh Babu", "Sunil Verma", "Ajay Meena",
        "Vikram Singh", "Pankaj Yadav", "Santosh Mane", "Ganesh Hegde", "Sandeep Chaudhary",
        "Manoj Tiwari", "Kishore Bhagat", "Harish Rao", "Pradeep Naik", "Nitin Gadkari",
        "Deepak Deshmukh", "Arun Jaitley", "Kapil Dev", "Sachin Kulkarni", "Virat Chauhan"
    ]
    
    # State-District mapping (Added Karnataka)
    geo_data = {
        "Tamil Nadu": {"district": "Thanjavur", "village": "Papanasam", "lat": 10.78, "lon": 79.13, "lang": "Tamil", "code": "TN"},
        "Andhra Pradesh": {"district": "Guntur", "village": "Tenali", "lat": 16.30, "lon": 80.43, "lang": "Telugu", "code": "AP"},
        "Maharashtra": {"district": "Jalna", "village": "Ambad", "lat": 19.84, "lon": 75.88, "lang": "Marathi", "code": "MH"},
        "Uttar Pradesh": {"district": "Varanasi", "village": "Rohaniya", "lat": 25.31, "lon": 82.97, "lang": "Hindi", "code": "UP"},
        "Karnataka": {"district": "Mandya", "village": "Maddur", "lat": 12.62, "lon": 77.04, "lang": "Kannada", "code": "KA"}
    }
    
    states_list = list(geo_data.keys())
    farmers = []
    
    for i in range(25):
        state_name = states_list[i % len(states_list)]
        data = geo_data[state_name]
        
        # Mandatory Coverage Constraints
        # 1. Urgency (5 farmers >= 0.7)
        urgency = round(random.uniform(0.7, 0.95), 2) if i < 5 else round(random.uniform(0.1, 0.6), 2)
        
        # 2. Device Type (At least 3 feature phones)
        if i < 3:
            device = "feature_phone"
        elif i % 5 == 0:
            device = "ios"
        else:
            device = "android"
            
        # 3. WhatsApp (At least 5 enabled)
        whatsapp = True if (i < 5 or i > 15) else False
        
        # 4. Connectivity (2G / 3G / 4G / offline)
        conn = random.choice(["2G", "3G", "4G", "offline"])
        
        # 5. Suppressed (3 messaged recently)
        if i >= 20 and i < 23:
            last_sent = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            msg_received = random.randint(8, 12) # High fatigue
        else:
            last_sent = (datetime.now() - timedelta(days=random.randint(5, 45))).strftime("%Y-%m-%d")
            msg_received = random.randint(1, 6)
            
        farmers.append(Farmer(
            farmer_id=f"{data['code']}-{100 + i:03d}",
            name=indian_names[i],
            age=random.randint(22, 68),
            phone=f"+91-9876543{i:03d}",
            preferred_language=data['lang'],
            state=state_name,
            district=data['district'],
            village=data['village'],
            latitude=round(data['lat'] + random.uniform(-0.02, 0.02), 4),
            longitude=round(data['lon'] + random.uniform(-0.02, 0.02), 4),
            acres=round(random.uniform(0.5, 12.0), 1),
            crops="rice" if i % 2 == 0 else "cotton", # Simplified to match example
            device_type=device,
            connectivity=conn,
            whatsapp_enabled=whatsapp,
            last_message_sent_at=last_sent,
            messages_received_last_30d=msg_received,
            messages_opened_last_30d=random.randint(0, msg_received),
            preferred_contact_time=random.choice(["morning", "afternoon", "evening"]),
            linked_retailer_id=f"RET-{random.randint(100, 999)}",
            linked_retailer_name=f"{indian_names[(i+7)%25]} Agro Agency",
            urgency_score=urgency
        ))
    
    for f in farmers:
        db.add(f)
    db.commit()

def seed_products(db: Session):
    db.query(Product).delete()
    base_path = "/home/yashvi/codes/Syngenta/product-catalog"
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
