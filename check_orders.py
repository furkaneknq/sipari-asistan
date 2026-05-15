import sys
sys.path.insert(0, "/home/furkan/Masaüstü/Proje/order_tracking")
from database.supabase_client import get_client

c = get_client()
r = c.table("orders").select("id,order_number,status,order_date,courier_id").limit(10).execute()
print(f"{len(r.data)} siparis bulundu")
for x in r.data:
    print(x)
