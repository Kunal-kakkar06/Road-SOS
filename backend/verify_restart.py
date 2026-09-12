import asyncio
import httpx
import sys

async def verify_restart():
    print("Verifying persistence across restarts...")
    with open("tokens.txt", "r") as f:
        tokens = f.read().splitlines()
    token_a = tokens[0]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        hist_a = await client.get("/api/triage/history", headers=headers_a)
        data = hist_a.json()
        assert len(data) >= 2, f"Expected at least 2 history records, got {len(data)}"
        print("[OK] History survives application restart (Count >= 2)")

if __name__ == "__main__":
    asyncio.run(verify_restart())
