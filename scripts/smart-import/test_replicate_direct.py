"""Direct Replicate API test via HTTP."""
import requests, json, base64, time, sys, os

sys.path.insert(0, os.path.dirname(__file__))
# Token from env (set in .env or system environment)
token = os.environ.get("REPLICATE_API_TOKEN", "")
assert token, "Set REPLICATE_API_TOKEN in .env"

with open("scripts/smart-import/dataset/poster-simple.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")

version = "da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595"
payload = {
    "version": version,
    "input": {
        "image": f"data:image/jpeg;base64,{b64}",
        "task_input": "OCR with Region",
    },
}

print("Creating prediction...")
r = requests.post(
    "https://api.replicate.com/v1/predictions",
    json=payload,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "wait=60",
    },
)
print(f"Status: {r.status_code}")
resp = r.json()

if r.status_code in (201, 200):
    print(f"ID: {resp.get('id')}")
    print(f"Status: {resp.get('status')}")
    if resp.get("output"):
        print(f"Output: {str(resp['output'])[:500]}")
    elif resp.get("status") in ("processing", "starting"):
        get_url = resp["urls"]["get"]
        for i in range(60):
            time.sleep(2)
            r2 = requests.get(get_url, headers={"Authorization": f"Bearer {token}"})
            d = r2.json()
            st = d.get("status")
            print(f"  Poll {i}: {st}  ({d.get('logs', '')[:60]})")
            if st in ("succeeded", "failed", "canceled"):
                print(f"Final output: {str(d.get('output', ''))[:500]}")
                if not d.get("output") and d.get("error"):
                    print(f"Error: {d['error']}")
                break
elif r.status_code == 402:
    print(f"INSUFFICIENT CREDIT: {json.dumps(resp, indent=2)[:300]}")
else:
    print(f"Error: {json.dumps(resp, indent=2)[:600]}")
