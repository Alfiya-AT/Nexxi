"""
probe_hf.py — Test which HF models are available on Serverless Inference API.
Run: python probe_hf.py
"""
import urllib.request
import json
from pathlib import Path

# Read token from .env
token = ""
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("HF_TOKEN=") and not line.startswith("#"):
            token = line.split("=", 1)[1].strip()
            break

if not token:
    print("ERROR: HF_TOKEN not found in .env")
    raise SystemExit(1)

print(f"Token: {token[:8]}...{token[-4:]}")
print()

MODELS = [
    "HuggingFaceH4/zephyr-7b-beta:fastest",
    "mistralai/Mistral-7B-Instruct-v0.2:fastest",
    "Qwen/Qwen2.5-7B-Instruct:fastest",
    "microsoft/Phi-3.5-mini-instruct:fastest",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0:fastest",
    "meta-llama/Llama-3.2-3B-Instruct:fastest",
    "deepseek-ai/DeepSeek-R1:fastest",
]

URL = "https://router.huggingface.co/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

print("Probing HuggingFace Serverless Inference API...")
print("-" * 60)

working = []
for model in MODELS:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Reply with: OK"}],
        "max_tokens": 10,
    }).encode("utf-8")

    req = urllib.request.Request(URL, data=payload, method="POST")
    for k, v in HEADERS.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.loads(res.read().decode("utf-8"))
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"  OK   {model}")
            print(f"       Reply: {reply[:60]!r}")
            working.append(model)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:100]
        print(f"  {e.code}  {model}")
        print(f"       {body}")
    except Exception as ex:
        print(f"  ERR  {model}")
        print(f"       {ex}")
    print()

print("-" * 60)
if working:
    print(f"Working models ({len(working)}):")
    for m in working:
        print(f"  - {m}")
    print()
    print(f"Set this in your .env:")
    print(f"  HF_MODEL_NAME={working[0]}")
else:
    print("No models worked. Check your HF_TOKEN or plan.")
