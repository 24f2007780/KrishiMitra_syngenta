import requests
import json

BASE_URL = "http://localhost:8002"

def run_rank_test(crop, pest, stage, urgency=0.5):
    print(f"\nTesting: Crop={crop}, Pest={pest}, Stage={stage}, Urgency={urgency}")
    
    payload = {
        "context": {
            "profile": {
                "farmer_id": "TEST-001",
                "name": "Test Farmer",
                "grower_age": 35,
                "phone": "+91-0000000000",
                "preferred_language": "English",
                "state": "Tamil Nadu",
                "district": "Thanjavur",
                "tehsil": "Test Village",
                "latitude": 10.78,
                "longitude": 79.13,
                "grower_farm_size": 5.0,
                "crops": [crop],
                "device_type": "android",
                "connectivity": "4G",
                "whatsapp_enabled": True,
                "last_message_sent_at": None,
                "messages_received_last_30d": 0,
                "messages_opened_last_30d": 0,
                "preferred_contact_time": "morning",
                "linked_retailer_id": "RET-001",
                "linked_retailer_name": "Test Retailer"
            },
            "signals": {
                "humidity_7d_avg": 85.0,
                "rainfall_deviation_pct": 20.0,
                "temperature_anomaly": 1.5,
                "pest_risk_level": "high",
                "active_pest": pest,
                "weather_anomaly_flag": True
            },
            "crop_stage": {
                "confirmed_stage": stage,
                "days_in_stage": 10,
                "vulnerability": "high",
                "days_to_next_stage": 20
            },
            "assembled_at": "2026-05-13T18:00:00Z"
        },
        "urgency_score": urgency
    }
    
    try:
        response = requests.post(f"{BASE_URL}/rank", json=payload["context"])
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2))
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    # Scenario 1: Rice + Fungal (Blight)
    run_rank_test("rice", "blight", "vegetative")
    
    # Scenario 2: Cotton + Aphid
    run_rank_test("cotton", "aphid", "flowering")
    
    # Scenario 3: Wheat + Rust
    run_rank_test("wheat", "rust", "vegetative")
    
    # Scenario 4: Seed Treatment
    run_rank_test("rice", "none", "seed_treatment")
