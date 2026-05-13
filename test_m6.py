import httpx
import asyncio

async def test_all_contexts():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Get all farmers
        print("Fetching all farmers from M1...")
        farmers_res = await client.get("http://localhost:8001/farmers")
        farmers = farmers_res.json()
        print(f"Found {len(farmers)} farmers.")

        # 2. Call M6 for each farmer
        print("Assembling contexts from M6...")
        farmer_ids = [f["farmer_id"] for f in farmers]
        
        # Test batch endpoint
        print("\nTesting batch endpoint...")
        try:
            batch_res = await client.post("http://localhost:8006/context/batch", json=farmer_ids)
            batch_data = batch_res.json()
            print(f"Batch assembled {len(batch_data)} contexts.")
        except Exception as e:
            print(f"Batch endpoint failed: {e}")

        # Test individual endpoint and check for errors
        print("\nTesting individual endpoints (sequentially)...")
        success_count = 0
        for fid in farmer_ids:
            try:
                res = await client.get(f"http://localhost:8006/context/{fid}")
                if res.status_code == 200:
                    success_count += 1
                    print(f"✅ Context assembled for farmer {fid}")
                    print(res.json())
                else:
                    print(f"❌ FAILED for farmer {fid}: {res.status_code} {res.text}")
            except Exception as e:
                print(f"❌ ERROR for farmer {fid}: {e}")
        
        print(f"\nFinal Result: {success_count}/{len(farmer_ids)} contexts assembled successfully.")

if __name__ == "__main__":
    asyncio.run(test_all_contexts())
