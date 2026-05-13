from fastapi import FastAPI, HTTPException
import requests
from datetime import datetime
import uvicorn
import os
import json

app = FastAPI()

CACHE_FILE = "ranking_service/cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
    return {"date": None, "data": None}

def save_cache(cache_data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=4)
    except Exception as e:
        print(f"Error saving cache: {e}")

CACHE = load_cache()


API_URL = "https://api.agmarknet.gov.in/v1/dashboard-data/"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0"
}

PAYLOAD = {
    "dashboard": "marketwise_price_arrival",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "group": [100000],
    "commodity": [100001],
    "variety": 100021,
    "state": 100006,
    "district": [100007],
    "market": [100009],
    "grades": [4],
    "limit": 10,
    "format": "json"
}



def fetch_page(page=1):

    response = requests.post(
        API_URL,
        headers=HEADERS,
        params={"page": page},
        json=PAYLOAD,
        timeout=30
    )

    response.raise_for_status()

    return response.json()



def scrape_all_pages():
    all_records = []
    try:
        # FIRST PAGE
        print(f"Fetching first page from {API_URL}...")
        first_page = fetch_page(1)
        
        if "pagination" not in first_page or "data" not in first_page:
            print(f"Unexpected response structure: {first_page.keys()}")
            return []

        pagination = first_page["pagination"]
        total_pages = pagination.get("total_pages", 1)
        print(f"Total pages: {total_pages}")

        # ADD PAGE 1 DATA
        records = first_page.get("data", {}).get("records", [])
        all_records.extend(records)
        print(f"Added {len(records)} records from page 1")

        # REMAINING PAGES
        for page in range(2, total_pages + 1):
            print(f"Fetching page {page}...")
            data = fetch_page(page)
            records = data.get("data", {}).get("records", [])
            all_records.extend(records)
            print(f"Added {len(records)} records from page {page}")

    except Exception as e:
        print(f"Error during scraping: {e}")
        # If we have some records, we can still return them, or re-raise
        if not all_records:
            raise e

    # CLEAN FORMAT
    cleaned = []
    for item in all_records:
        cleaned.append({
            "commodity_group": item.get("cmdt_grp_name"),
            "commodity": item.get("cmdt_name"),
            "msp_rs_quintal": item.get("msp_price"),
            "today_price_rs_quintal": item.get("as_on_price"),
            "today_arrival_metric_tonnes": item.get("as_on_arrival"),
            "trend": item.get("trend"),
            "reported_date": item.get("reported_date")
        })
    
    print(f"Total cleaned records: {len(cleaned)}")
    return cleaned



def get_cached_data():

    today = datetime.now().strftime("%Y-%m-%d")

    # CACHE HIT
    if CACHE["date"] == today and CACHE["data"] is not None:

        print("Serving from cache")

        return CACHE["data"]

    # CACHE MISS
    print("Refreshing cache")

    data = scrape_all_pages()

    CACHE["date"] = today
    CACHE["data"] = data

    save_cache(CACHE)

    return data



@app.get("/")
def home():

    return {
        "message": "Agmarknet API Running",
        "cached_date": CACHE["date"]
    }


@app.get("/today")
def today_prices():

    try:

        data = get_cached_data()

        return {
            "count": len(data),
            "data": data
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/commodity/{commodity_name}")
def commodity_data(commodity_name: str):

    data = get_cached_data()

    filtered = [

        item for item in data

        if commodity_name.lower()
        in item["commodity"].lower()
    ]

    return {
        "count": len(filtered),
        "data": filtered
    }



@app.on_event("startup")
def startup_event():

    try:

        print("Preloading cache")

        get_cached_data()

    except Exception as e:

        print("Startup cache failed:", e)


if __name__ == "__main__":

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )