import sys
sys.path.insert(0, "C:/Users/User/Desktop/Proje/order_tracking")
from database.supabase_client import get_client
from utils.helpers import normalize_phone
import csv
import io
import re

SQL_FILE = "C:/Users/User/Desktop/Proje/siparisasistan.sql"

def parse_mysql_values(line):
    line = line.strip()
    if line.startswith('('):
        line = line[1:]
    if line.endswith(');'):
        line = line[:-2]
    elif line.endswith('),'):
        line = line[:-2]
    elif line.endswith(')'):
        line = line[:-1]
    
    # Use csv module to parse
    f = io.StringIO(line)
    reader = csv.reader(f, delimiter=',', quotechar="'", escapechar='\\', skipinitialspace=True)
    try:
        row = next(reader)
        return [col if col != 'NULL' else '' for col in row]
    except StopIteration:
        return []

def run():
    client = get_client()
    
    # 1. Fetch existing customers to avoid duplicates
    print("Mevcut müşteriler getiriliyor...")
    existing_phones = set()
    offset = 0
    limit = 1000
    while True:
        res = client.table("customers").select("phone").range(offset, offset+limit-1).execute()
        if not res.data:
            break
        for c in res.data:
            existing_phones.add(c["phone"])
        if len(res.data) < limit:
            break
        offset += limit
    print(f"{len(existing_phones)} mevcut müşteri bulundu.")
    
    new_customers = []
    seen_phones = set()
    skipped = 0
    
    print("SQL dosyası okunuyor...")
    with open(SQL_FILE, 'r', encoding='cp1254', errors='ignore') as f:
        in_insert = False
        for line in f:
            if line.startswith("INSERT INTO `musteriler` VALUES"):
                in_insert = True
                continue
            
            if in_insert:
                if not line.strip():
                    continue
                
                row = parse_mysql_values(line)
                if len(row) > 32:
                    name_raw = row[3]
                    addr1_raw = row[4]
                    phone_raw = row[7]
                    addr2_raw = row[32]
                    
                    name = name_raw.strip().upper()
                    addr1 = addr1_raw.strip().upper()
                    addr2 = addr2_raw.strip().upper()
                    phone = normalize_phone(phone_raw)
                    
                    if not phone or not name:
                        skipped += 1
                    elif phone in existing_phones or phone in seen_phones:
                        skipped += 1
                    else:
                        new_customers.append({
                            "name": name,
                            "phone": phone,
                            "addr1": addr1,
                            "addr2": addr2
                        })
                        seen_phones.add(phone)
                
                if line.strip().endswith(';'):
                    in_insert = False
                    
    print(f"Eklenecek yeni müşteri sayısı: {len(new_customers)}, Atlanan: {skipped}")
    
    # Bulk insert
    BATCH_SIZE = 500
    inserted = 0
    total = len(new_customers)
    
    for i in range(0, total, BATCH_SIZE):
        batch = new_customers[i:i+BATCH_SIZE]
        
        # Insert customers
        cust_payload = [{"name": c["name"], "phone": c["phone"]} for c in batch]
        res = client.table("customers").insert(cust_payload).execute()
        
        if not res.data:
            print(f"HATA: Batch {i}-{i+len(batch)} eklenemedi")
            continue
            
        # Insert addresses
        addr_payload = []
        for cust_data, cust_row in zip(res.data, batch):
            cust_id = cust_data["id"]
            if cust_row["addr1"]:
                addr_payload.append({
                    "customer_id": cust_id,
                    "title": "ADRES 1",
                    "address_text": cust_row["addr1"],
                    "is_default": True
                })
            if cust_row["addr2"]:
                addr_payload.append({
                    "customer_id": cust_id,
                    "title": "ADRES 2",
                    "address_text": cust_row["addr2"],
                    "is_default": False
                })
                
        if addr_payload:
            client.table("customer_addresses").insert(addr_payload).execute()
            
        inserted += len(batch)
        print(f"İlerleme: {inserted}/{total}")
        
    print(f"Tamamlandı: {inserted} müşteri başarıyla eklendi.")

if __name__ == "__main__":
    run()
