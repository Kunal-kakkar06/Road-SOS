import asyncio
import httpx
import time

async def verify():
    print("Verifying Async Triage Pipeline")
    
    with open("tokens.txt", "r") as f:
        tokens = f.read().splitlines()
    token_a, token_b = tokens[0], tokens[1]
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # 1. Start job for User A
        start_time = time.time()
        resp = await client.post("/api/triage/async", json={"text": "Severe chest pain"}, headers=headers_a)
        latency = time.time() - start_time
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"
        
        data = resp.json()
        job_id = data["job_id"]
        print(f"[OK] POST /api/triage/async returned 202 in {latency:.4f}s. Job ID: {job_id}")
        assert data["status"] == "pending"
        
        # 2. Poll for transition
        processing_seen = False
        completed = False
        
        for i in range(20):
            status_resp = await client.get(f"/api/triage/jobs/{job_id}", headers=headers_a)
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            st = status_data["status"]
            print(f"Poll {i}: {st}")
            
            if st == "processing":
                processing_seen = True
            elif st == "completed":
                completed = True
                assert "result" in status_data
                break
            await asyncio.sleep(0.5)
            
        assert completed, "Job did not complete in time"
        print("[OK] Job transitioned to completed.")
        
        # 3. Ownership isolation
        resp_b = await client.get(f"/api/triage/jobs/{job_id}", headers=headers_b)
        assert resp_b.status_code == 404, "User B should not be able to access User A's job"
        print("[OK] User B received 404 for User A's job.")

if __name__ == "__main__":
    asyncio.run(verify())
