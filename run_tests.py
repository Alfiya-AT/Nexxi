"""
run_tests.py — Comprehensive Nexxi Lite API Test Suite
Tests all endpoints, edge cases, session management, and error handling.
Run with: python run_tests.py
"""

import httpx
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT  = 60.0

# ── Colour helpers ──────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

passed = 0
failed = 0
skipped = 0
results = []

def log(symbol, label, msg, colour=RESET):
    print(f"  {colour}{symbol} {label}{RESET}: {msg}")

def section(title):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")

def record(name, ok, detail="", skip=False):
    global passed, failed, skipped
    if skip:
        skipped += 1
        log("⏭", name, detail, YELLOW)
        results.append(("SKIP", name, detail))
    elif ok:
        passed += 1
        log("✅", name, detail, GREEN)
        results.append(("PASS", name, detail))
    else:
        failed += 1
        log("❌", name, detail, RED)
        results.append(("FAIL", name, detail))


# ══════════════════════════════════════════════════════════════
# 1. HEALTH & READINESS
# ══════════════════════════════════════════════════════════════
section("1 · Health & Readiness Checks")

with httpx.Client(timeout=10) as c:

    # TC-01: GET /health
    try:
        r = c.get(f"{BASE_URL}/health")
        ok = r.status_code == 200
        d  = r.json()
        record("TC-01 GET /health → 200", ok,
               f"status={d.get('status')} | token_set={d.get('hf_token_set')} | model={d.get('active_model','?').split('/')[-1]}")
    except Exception as e:
        record("TC-01 GET /health → 200", False, str(e))

    # TC-02: /health contains expected keys
    try:
        r = c.get(f"{BASE_URL}/health")
        d = r.json()
        keys = {"status","service","mode","active_model","candidates","hf_token_set","timestamp"}
        missing = keys - set(d.keys())
        record("TC-02 /health payload keys", not missing,
               f"missing={missing}" if missing else "all keys present")
    except Exception as e:
        record("TC-02 /health payload keys", False, str(e))

    # TC-03: GET /ready
    try:
        r = c.get(f"{BASE_URL}/ready")
        ok = r.status_code == 200
        d  = r.json()
        record("TC-03 GET /ready → 200", ok,
               f"status={d.get('status')} | model={d.get('active_model','?').split('/')[-1]}")
    except Exception as e:
        record("TC-03 GET /ready → 200", False, str(e))

    # TC-04: Root endpoint exists
    try:
        r = c.get(f"{BASE_URL}/")
        record("TC-04 GET / → 200 or 404", r.status_code in (200, 404),
               f"HTTP {r.status_code}")
    except Exception as e:
        record("TC-04 GET / → 200 or 404", False, str(e))

    # TC-05: /docs (Swagger) available
    try:
        r = c.get(f"{BASE_URL}/docs")
        record("TC-05 GET /docs (Swagger)", r.status_code == 200,
               f"HTTP {r.status_code}")
    except Exception as e:
        record("TC-05 GET /docs (Swagger)", False, str(e))


# ══════════════════════════════════════════════════════════════
# 2. CHAT — BASIC FUNCTIONALITY
# ══════════════════════════════════════════════════════════════
section("2 · Chat API — Basic Functionality")

with httpx.Client(timeout=TIMEOUT) as c:

    # TC-06: Simple greeting
    try:
        print(f"  {YELLOW}⏳ TC-06: Sending greeting (may take ~10s)…{RESET}")
        t0 = time.time()
        r  = c.post(f"{BASE_URL}/v1/chat", json={"message": "Hello! What is your name?"})
        elapsed = round(time.time() - t0, 2)
        ok = r.status_code == 200
        d  = r.json() if ok else {}
        reply_snippet = d.get("message","")[:80].replace('\n',' ')
        record("TC-06 Simple greeting", ok,
               f"HTTP {r.status_code} | {elapsed}s | reply: '{reply_snippet}…'")
        SESSION_ID = d.get("session_id","") if ok else ""
    except Exception as e:
        record("TC-06 Simple greeting", False, str(e))
        SESSION_ID = ""

    # TC-07: Response schema validation
    try:
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": "What can you help me with?"})
        d = r.json()
        keys = {"session_id","message","model","tokens_used","response_time_ms","timestamp"}
        missing = keys - set(d.keys())
        record("TC-07 Response schema", not missing and r.status_code == 200,
               f"missing={missing}" if missing else f"tokens={d.get('tokens_used')} | model={d.get('model','?')}")
    except Exception as e:
        record("TC-07 Response schema", False, str(e))

    # TC-08: Session continuity (multi-turn)
    if SESSION_ID:
        try:
            print(f"  {YELLOW}⏳ TC-08: Testing session memory…{RESET}")
            r1 = c.post(f"{BASE_URL}/v1/chat",
                        json={"message": "My favourite colour is electric blue.", "session_id": SESSION_ID})
            r2 = c.post(f"{BASE_URL}/v1/chat",
                        json={"message": "What is my favourite colour?", "session_id": SESSION_ID})
            reply2 = r2.json().get("message","").lower()
            ok = "blue" in reply2
            record("TC-08 Session memory (multi-turn)", ok,
                   f"remembered: {'yes' if ok else 'NO'} | reply: '{reply2[:80]}…'")
        except Exception as e:
            record("TC-08 Session memory (multi-turn)", False, str(e))
    else:
        record("TC-08 Session memory (multi-turn)", False, skip=True,
               detail="Skipped — no session_id from TC-06")

    # TC-09: Factual knowledge question
    try:
        print(f"  {YELLOW}⏳ TC-09: Factual question…{RESET}")
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": "What is 15 * 7? Just give the number."})
        reply = r.json().get("message","")
        ok = "105" in reply
        record("TC-09 Factual (15*7=105)", ok,
               f"reply: '{reply[:80]}'")
    except Exception as e:
        record("TC-09 Factual (15*7=105)", False, str(e))

    # TC-10: Coding question
    try:
        print(f"  {YELLOW}⏳ TC-10: Coding question…{RESET}")
        r = c.post(f"{BASE_URL}/v1/chat",
                   json={"message": "Write a Python function that returns the factorial of n. Only give code, no explanation."})
        reply = r.json().get("message","")
        ok = "def" in reply and "factorial" in reply.lower()
        record("TC-10 Code generation (factorial)", ok,
               f"contains 'def': {'yes' if ok else 'NO'} | snippet: '{reply[:80]}'")
    except Exception as e:
        record("TC-10 Code generation (factorial)", False, str(e))


# ══════════════════════════════════════════════════════════════
# 3. INPUT VALIDATION & EDGE CASES
# ══════════════════════════════════════════════════════════════
section("3 · Input Validation & Edge Cases")

with httpx.Client(timeout=10) as c:

    # TC-11: Empty message → 422
    try:
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": ""})
        record("TC-11 Empty message → 422", r.status_code == 422,
               f"HTTP {r.status_code} (expected 422)")
    except Exception as e:
        record("TC-11 Empty message → 422", False, str(e))

    # TC-12: Missing 'message' field → 422
    try:
        r = c.post(f"{BASE_URL}/v1/chat", json={})
        record("TC-12 Missing message field → 422", r.status_code == 422,
               f"HTTP {r.status_code} (expected 422)")
    except Exception as e:
        record("TC-12 Missing message field → 422", False, str(e))

    # TC-13: Message too long (>1000 chars) → 422
    try:
        long_msg = "A" * 1001
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": long_msg})
        record("TC-13 Message > 1000 chars → 422", r.status_code == 422,
               f"HTTP {r.status_code} (expected 422)")
    except Exception as e:
        record("TC-13 Message > 1000 chars → 422", False, str(e))

    # TC-14: Exactly 1000 chars (boundary — should be allowed)
    try:
        boundary_msg = "B" * 1000
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": boundary_msg})
        record("TC-14 Message = 1000 chars (boundary)", r.status_code != 422,
               f"HTTP {r.status_code}")
    except Exception as e:
        record("TC-14 Message = 1000 chars (boundary)", False, str(e))

    # TC-15: Non-JSON body → 422
    try:
        r = c.post(f"{BASE_URL}/v1/chat",
                   content=b"not-json",
                   headers={"Content-Type": "application/json"})
        record("TC-15 Non-JSON body → 422", r.status_code == 422,
               f"HTTP {r.status_code}")
    except Exception as e:
        record("TC-15 Non-JSON body → 422", False, str(e))

    # TC-16: Special characters in message
    try:
        r = c.post(f"{BASE_URL}/v1/chat",
                   json={"message": "Translate: café, résumé, naïve 🌍"}, timeout=TIMEOUT)
        record("TC-16 Special chars & emoji", r.status_code == 200,
               f"HTTP {r.status_code}")
    except Exception as e:
        record("TC-16 Special chars & emoji", False, str(e))

    # TC-17: Numeric message (still valid string)
    try:
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": "42"}, timeout=TIMEOUT)
        record("TC-17 Numeric string message", r.status_code == 200,
               f"HTTP {r.status_code}")
    except Exception as e:
        record("TC-17 Numeric string message", False, str(e))


# ══════════════════════════════════════════════════════════════
# 4. SESSION MANAGEMENT
# ══════════════════════════════════════════════════════════════
section("4 · Session Management")

with httpx.Client(timeout=TIMEOUT) as c:

    # TC-18: Auto session_id creation
    try:
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": "Hi there!"})
        sid = r.json().get("session_id","")
        record("TC-18 Auto session_id created", bool(sid) and r.status_code == 200,
               f"session_id='{sid[:20]}…'")
    except Exception as e:
        record("TC-18 Auto session_id created", False, str(e))

    # TC-19: Custom session_id respected
    try:
        custom_sid = "nexxi-test-custom-session-abc123"
        r = c.post(f"{BASE_URL}/v1/chat",
                   json={"message": "Hello.", "session_id": custom_sid})
        returned_sid = r.json().get("session_id","")
        ok = returned_sid == custom_sid
        record("TC-19 Custom session_id preserved", ok,
               f"sent='{custom_sid}' | returned='{returned_sid}'")
    except Exception as e:
        record("TC-19 Custom session_id preserved", False, str(e))

    # TC-20: Delete session
    try:
        sid = "nexxi-test-delete-session-xyz"
        # First create it
        c.post(f"{BASE_URL}/v1/chat", json={"message": "Remember me.", "session_id": sid})
        # Then delete it
        r = c.delete(f"{BASE_URL}/v1/chat/session", json={"session_id": sid})
        d = r.json()
        ok = r.status_code == 200 and d.get("status") == "cleared"
        record("TC-20 DELETE /v1/chat/session", ok,
               f"HTTP {r.status_code} | status={d.get('status')}")
    except Exception as e:
        record("TC-20 DELETE /v1/chat/session", False, str(e))

    # TC-21: Delete non-existent session (should be graceful)
    try:
        r = c.delete(f"{BASE_URL}/v1/chat/session",
                     json={"session_id": "session-that-never-existed-99999"})
        record("TC-21 Delete non-existent session (graceful)", r.status_code == 200,
               f"HTTP {r.status_code}")
    except Exception as e:
        record("TC-21 Delete non-existent session (graceful)", False, str(e))

    # TC-22: Two parallel sessions are independent
    try:
        print(f"  {YELLOW}⏳ TC-22: Testing session isolation…{RESET}")
        sid_a = "nexxi-isolation-A"
        sid_b = "nexxi-isolation-B"
        c.post(f"{BASE_URL}/v1/chat",
               json={"message": "My pet is a red dragon.", "session_id": sid_a})
        c.post(f"{BASE_URL}/v1/chat",
               json={"message": "My pet is a golden eagle.", "session_id": sid_b})
        ra = c.post(f"{BASE_URL}/v1/chat",
                    json={"message": "What is my pet?", "session_id": sid_a})
        rb = c.post(f"{BASE_URL}/v1/chat",
                    json={"message": "What is my pet?", "session_id": sid_b})
        reply_a = ra.json().get("message","").lower()
        reply_b = rb.json().get("message","").lower()
        ok = ("dragon" in reply_a or "red" in reply_a) and ("eagle" in reply_b or "golden" in reply_b)
        record("TC-22 Session isolation", ok,
               f"A mentions dragon={'dragon' in reply_a} | B mentions eagle={'eagle' in reply_b}")
        # Cleanup
        for sid in [sid_a, sid_b]:
            c.delete(f"{BASE_URL}/v1/chat/session", json={"session_id": sid})
    except Exception as e:
        record("TC-22 Session isolation", False, str(e))


# ══════════════════════════════════════════════════════════════
# 5. RESPONSE QUALITY
# ══════════════════════════════════════════════════════════════
section("5 · Response Quality Checks")

with httpx.Client(timeout=TIMEOUT) as c:

    # TC-23: Response time is reasonable
    try:
        t0 = time.time()
        r  = c.post(f"{BASE_URL}/v1/chat", json={"message": "Say 'hello'."})
        rt = (time.time() - t0) * 1000
        d  = r.json()
        reported_ms = d.get("response_time_ms", 0)
        ok = r.status_code == 200 and reported_ms > 0
        record("TC-23 Response time field populated", ok,
               f"reported={reported_ms}ms | wall-clock={round(rt)}ms")
    except Exception as e:
        record("TC-23 Response time field", False, str(e))

    # TC-24: tokens_used > 0
    try:
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": "Tell me a one-sentence joke."})
        tokens = r.json().get("tokens_used", 0)
        record("TC-24 tokens_used > 0", tokens > 0,
               f"tokens_used={tokens}")
    except Exception as e:
        record("TC-24 tokens_used > 0", False, str(e))

    # TC-25: Model field is set (not empty)
    try:
        r = c.post(f"{BASE_URL}/v1/chat", json={"message": "Hi"})
        model = r.json().get("model","")
        record("TC-25 model field not empty", bool(model),
               f"model='{model}'")
    except Exception as e:
        record("TC-25 model field not empty", False, str(e))

    # TC-26: timestamp is valid ISO-8601
    try:
        r  = c.post(f"{BASE_URL}/v1/chat", json={"message": "Hi"})
        ts = r.json().get("timestamp","")
        dt = datetime.fromisoformat(ts.replace("Z","+00:00"))
        record("TC-26 timestamp is valid ISO-8601", True,
               f"timestamp='{ts[:25]}'")
    except Exception as e:
        record("TC-26 timestamp is valid ISO-8601", False, str(e))

    # TC-27: Model does NOT reveal its underlying identity
    try:
        r = c.post(f"{BASE_URL}/v1/chat",
                   json={"message": "What model are you? What is your underlying AI architecture?"})
        reply = r.json().get("message","").lower()
        leaked = any(x in reply for x in ["deepseek","llama","mistral","qwen","gpt","claude"])
        record("TC-27 Model identity masked", not leaked,
               f"leaked name: {'YES ⚠' if leaked else 'no'} | snippet: '{reply[:80]}'")
    except Exception as e:
        record("TC-27 Model identity masked", False, str(e))


# ══════════════════════════════════════════════════════════════
# 6. CONCURRENT REQUESTS
# ══════════════════════════════════════════════════════════════
section("6 · Concurrency Stress Test")

import threading

concurrent_results = []

def fire_request(idx):
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.post(f"{BASE_URL}/v1/chat",
                       json={"message": f"Say exactly: 'Request {idx} OK'"})
            concurrent_results.append(r.status_code == 200)
    except Exception:
        concurrent_results.append(False)

# TC-28: 5 concurrent requests
try:
    print(f"  {YELLOW}⏳ TC-28: Firing 5 concurrent requests…{RESET}")
    threads = [threading.Thread(target=fire_request, args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=TIMEOUT)
    all_ok = all(concurrent_results) and len(concurrent_results) == 5
    record("TC-28 5 concurrent requests", all_ok,
           f"passed={sum(concurrent_results)}/5")
except Exception as e:
    record("TC-28 5 concurrent requests", False, str(e))


# ══════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════
total = passed + failed + skipped
print(f"\n{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  NEXXI LITE — TEST REPORT{RESET}")
print(f"{BOLD}{'═'*60}{RESET}")
print(f"  {GREEN}PASSED : {passed}{RESET}")
print(f"  {RED}FAILED : {failed}{RESET}")
print(f"  {YELLOW}SKIPPED: {skipped}{RESET}")
print(f"  TOTAL  : {total}")
score = round(passed / max(passed+failed,1) * 100)
colour = GREEN if score >= 80 else (YELLOW if score >= 60 else RED)
print(f"\n  {colour}{BOLD}Score: {score}% ({passed}/{passed+failed} run){RESET}")

if failed > 0:
    print(f"\n{RED}  Failed tests:{RESET}")
    for status, name, detail in results:
        if status == "FAIL":
            print(f"    {RED}• {name}{RESET}: {detail}")

print(f"\n{BOLD}{'═'*60}{RESET}\n")
sys.exit(0 if failed == 0 else 1)
