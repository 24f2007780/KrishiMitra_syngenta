import httpx
import asyncio

async def run_test_all_contexts():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Get all farmers
        print("Fetching all farmers from M1...")
        farmers_res = await client.get("http://localhost:8001/farmers")
        farmers = farmers_res.json()
        print(f"Found {len(farmers)} farmers.")

        # 2. Call M6 for each farmer
        print("Assembling contexts from M6...")
        grower_ids = [f["grower_id"] for f in farmers][:5]
        
        # Test batch endpoint
        print("\nTesting batch endpoint...")
        try:
            batch_res = await client.post("http://localhost:8006/context/batch", json=grower_ids)
            batch_data = batch_res.json()
            print(f"Batch assembled {len(batch_data)} contexts.")
        except Exception as e:
            print(f"Batch endpoint failed: {e}")

        # Test individual endpoint and check for errors
        print("\nTesting individual endpoints (sequentially)...")
        success_count = 0
        for fid in grower_ids:
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
        
        print(f"\nFinal Result: {success_count}/{len(grower_ids)} contexts assembled successfully.")

if __name__ == "__main__":
    asyncio.run(run_test_all_contexts())
