"""Check Qwen2.5-VL on OpenRouter."""
import os, requests, json

key = os.environ.get("OPENROUTER_API_KEY", "")
r = requests.get("https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {key}"})
models = r.json().get("data", [])
for m in models:
    mid = m["id"]
    if "qwen" in mid.lower() and "vl" in mid.lower():
        pricing = m.get("pricing", {})
        prompt_cost = float(pricing.get("prompt", 0)) * 1_000_000
        print(f"{mid}")
        print(f"  Context: {m.get('context_length','?')}")
        print(f"  Cost: {prompt_cost:.4f}/M tokens prompt")
        print()
