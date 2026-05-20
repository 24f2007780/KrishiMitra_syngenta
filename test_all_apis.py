import json
import requests
import sys

# Define base URLs for all active microservices in run_all.sh
M1_URL = "http://localhost:8001"  # Farmer Service
M2_URL = "http://localhost:8008"  # Product Service (M8 Ranker)
M4_URL = "http://localhost:8004"  # Weather Service
M5_URL = "http://localhost:8005"  # Calendar Service
M6_URL = "http://localhost:8006"  # Context Service
M7_URL = "http://localhost:8007"  # Urgency Scorer
M16_URL = "http://localhost:8009" # Campaign Receptivity Engine

def print_section(title):
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)

def print_result(api_name, response):
    print(f"\n🔹 {api_name}")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2))
    except Exception:
        print("Response Text (Non-JSON):")
        print(response.text[:500])

def main():
    print_section("SYNGENTA KRISHIMITRA — MICROSERVICES ROUTE VERIFICATION")

    # ==================== PORT 8001: M1 FARMER SERVICE ====================
    print_section("M1: FARMER SERVICE (Port 8001)")
    try:
        # 1. POST /farmers/seed
        res = requests.post(f"{M1_URL}/farmers/seed")
        print_result("POST /farmers/seed", res)

        # 2. GET /farmers
        res = requests.get(f"{M1_URL}/farmers")
        print_result("GET /farmers", res)
        farmers = res.json()
        
        # Select a sample farmer for subsequent tests
        sample_grower_id = farmers[0]["grower_id"] if farmers else "GRW_00001"
        print(f"\nSelected Sample Farmer ID: {sample_grower_id}")

        # 3. GET /farmer/{grower_id}
        res = requests.get(f"{M1_URL}/farmer/{sample_grower_id}")
        print_result(f"GET /farmer/{sample_grower_id}", res)
        farmer_profile = res.json()
    except Exception as e:
        print(f"❌ M1 Test Failed: {e}")
        sys.exit(1)

    # ==================== PORT 8004: M4 WEATHER SERVICE ====================
    print_section("M4: WEATHER SERVICE (Port 8004)")
    try:
        lat = farmer_profile.get("latitude", 27.0238)
        lon = farmer_profile.get("longitude", 74.2179)

        # 1. GET /signals/weather
        res = requests.get(f"{M4_URL}/signals/weather", params={"lat": lat, "lon": lon})
        print_result(f"GET /signals/weather (lat={lat}, lon={lon})", res)

        # 2. GET /debug/weather
        res = requests.get(f"{M4_URL}/debug/weather", params={"lat": lat, "lon": lon})
        print_result(f"GET /debug/weather (lat={lat}, lon={lon})", res)
    except Exception as e:
        print(f"❌ M4 Test Failed: {e}")

    # ==================== PORT 8005: M5 CROP CALENDAR SERVICE ====================
    print_section("M5: CROP CALENDAR SERVICE (Port 8005)")
    try:
        # 1. GET /
        res = requests.get(f"{M5_URL}/")
        print_result("GET /", res)

        # 2. GET /calendar
        state = farmer_profile.get("state", "Punjab")
        crop = farmer_profile.get("crops", ["wheat"])[0]
        res = requests.get(f"{M5_URL}/calendar", params={"state": state, "crop": crop})
        print_result(f"GET /calendar (state={state}, crop={crop})", res)
    except Exception as e:
        print(f"❌ M5 Test Failed: {e}")

    # ==================== PORT 8006: M6 CONTEXT ASSEMBLER ====================
    print_section("M6: CONTEXT ASSEMBLER (Port 8006)")
    farmer_context = None
    try:
        # 1. GET /context/{grower_id}
        res = requests.get(f"{M6_URL}/context/{sample_grower_id}")
        print_result(f"GET /context/{sample_grower_id}", res)
        if res.status_code == 200:
            farmer_context = res.json()

        # 2. POST /context/batch
        grower_ids = [f["grower_id"] for f in farmers[:5]]
        res = requests.post(f"{M6_URL}/context/batch", json=grower_ids)
        print_result("POST /context/batch (5 Farmers)", res)
    except Exception as e:
        print(f"❌ M6 Test Failed: {e}")

    if not farmer_context:
        print("⚠️ Warning: Skipping down-stream tests that require a valid FarmerContext due to M6 context assembly failure.")
        sys.exit(1)

    # ==================== PORT 8007: M7 URGENCY SCORER ====================
    print_section("M7: URGENCY SCORER SERVICE (Port 8007)")
    try:
        # 1. POST /score
        res = requests.post(f"{M7_URL}/score", json=farmer_context)
        print_result("POST /score", res)

        # 2. POST /explain
        res = requests.post(f"{M7_URL}/explain", json=farmer_context)
        print_result("POST /explain (HTML explainer response - truncated)", res)
    except Exception as e:
        print(f"❌ M7 Test Failed: {e}")

    # ==================== PORT 8002: M2/M8 PRODUCT RANKER ====================
    print_section("M2/M8: PRODUCT RANKER SERVICE (Port 8002)")
    try:
        # 1. POST /rank
        res = requests.post(f"{M2_URL}/rank", json=farmer_context)
        print_result("POST /rank", res)

        # 2. GET /products/{grower_id}
        res = requests.get(f"{M2_URL}/products/{sample_grower_id}")
        print_result(f"GET /products/{sample_grower_id}", res)
    except Exception as e:
        print(f"❌ M2 Test Failed: {e}")

    # ==================== PORT 8008: M16 CAMPAIGN ORCHESTRATOR ====================
    print_section("M16: CAMPAIGN RECEPTIVITY SERVICE (Port 8008)")
    try:
        # Map device type string to valid DeviceType enum values
        device_raw = farmer_profile.get("device_type", "smartphone")
        device_mapped = "smartphone"
        if device_raw:
            device_lower = str(device_raw).lower()
            if "keypad" in device_lower or "feature" in device_lower:
                device_mapped = "keypad"
            elif "smartphone" in device_lower or "android" in device_lower or "ios" in device_lower:
                device_mapped = "smartphone"
            else:
                device_mapped = "unknown"

        # Prepare ReceptivityRequest payload structure from farmer_profile
        receptivity_request = {
            "grower_id": sample_grower_id,
            "crop": farmer_profile.get("crops", ["wheat"])[0],
            "district": farmer_profile.get("district", "Jaipur"),
            "device_type": device_mapped,
            "farm_size_acres": farmer_profile.get("grower_farm_size", 2.0),
            "grower_age": farmer_profile.get("grower_age", 40),
            "campaign_product": "Kavach 75 WP"
        }

        # 1. POST /predict
        res = requests.post(f"{M16_URL}/predict", json=receptivity_request)
        print_result("POST /predict", res)

        # 2. GET /predict/{grower_id}
        res = requests.get(f"{M16_URL}/predict/{sample_grower_id}")
        print_result(f"GET /predict/{sample_grower_id}", res)

        # 3. POST /explain
        res = requests.post(f"{M16_URL}/explain", json=receptivity_request)
        print_result("POST /explain (HTML explainer response - truncated)", res)
    except Exception as e:
        print(f"❌ M16 Test Failed: {e}")

    print_section("ALL ROUTE VERIFICATION COMPLETED")

if __name__ == "__main__":
    main()
