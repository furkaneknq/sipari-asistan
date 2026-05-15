"""courier_save_address_location RPC'si var mı test et."""
import sys
sys.path.insert(0, "/home/furkan/Masaüstü/Proje/order_tracking")
import httpx
import config

url = config.SUPABASE_URL
key = config.SUPABASE_KEY
courier_id = "c14122c8-4a8f-4733-a385-9c1686592ed7"

# 1) courier_save_address_location RPC var mı?
print("courier_save_address_location RPC test...")
resp = httpx.post(
    f"{url}/rest/v1/rpc/courier_save_address_location",
    headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={
        "p_address_id": "70acb8c7-37ef-4b19-9765-7c5c97f9f325",
        "p_courier_id": courier_id,
        "p_latitude": "37.123456",
        "p_longitude": "38.654321"
    }
)
print(f"  HTTP {resp.status_code}")
print(f"  Yanit: {resp.text[:300]}")

# 2) Adresteki konum güncellendi mi?
print("\nAdres kontrol:")
from database.supabase_client import get_client
c = get_client()
addr = c.table("customer_addresses").select("id,address_text,latitude,longitude").eq("id", "70acb8c7-37ef-4b19-9765-7c5c97f9f325").limit(1).execute()
for a in (addr.data or []):
    print(f"  {a}")
