import requests, json

print("=== TEST 1: simple/price with ids=pharos ===")
r1 = requests.get(
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=pharos&vs_currencies=usd&include_market_cap=true&include_24hr_change=true&include_24hr_vol=true",
    timeout=10, headers={"Accept": "application/json"}
)
print("Status:", r1.status_code)
try: print(json.dumps(r1.json(), indent=2))
except: print("Response:", r1.text[:200])

print()
print("=== TEST 2: simple/price with ids=pharos-network ===")
r2 = requests.get(
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=pharos-network&vs_currencies=usd&include_market_cap=true&include_24hr_change=true&include_24hr_vol=true",
    timeout=10, headers={"Accept": "application/json"}
)
print("Status:", r2.status_code)
try: print(json.dumps(r2.json(), indent=2))
except: print("Response:", r2.text[:200])

print()
print("=== TEST 3: coins/markets with ids=pharos ===")
r3 = requests.get(
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&ids=pharos&price_change_percentage=24h",
    timeout=10, headers={"Accept": "application/json"}
)
print("Status:", r3.status_code)
try:
    d = r3.json()
    if d:
        c = d[0]
        print(f"name={c['name']} symbol={c['symbol']}")
        print(f"price={c['current_price']} mcap={c['market_cap']} vol={c['total_volume']}")
    else:
        print("empty []")
except: print("Response:", r3.text[:200])

print()
print("=== TEST 4: search for PROS ===")
r4 = requests.get(
    "https://api.coingecko.com/api/v3/search?query=PROS",
    timeout=10, headers={"Accept": "application/json"}
)
print("Status:", r4.status_code)
try:
    coins = r4.json().get("coins", [])[:6]
    for c in coins:
        print(f"  id={c['id']}  symbol={c['symbol']}  name={c['name']}")
except: print("Response:", r4.text[:200])