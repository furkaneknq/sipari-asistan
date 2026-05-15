"""Tüm müşterileri sil ve Sayfa2.xlsx'ten baştan yükle."""
import sys
sys.path.insert(0, "/home/furkan/Masaüstü/Proje/order_tracking")

import openpyxl
from database.supabase_client import get_client
from utils.helpers import normalize_phone

EXCEL_PATH = "/home/furkan/Masaüstü/Proje/Sayfa2.xlsx"
BATCH_SIZE = 500


def delete_all_customers():
    """Tüm müşteri verisini sil (bağımlılık sırasıyla)."""
    client = get_client()
    dummy = "00000000-0000-0000-0000-000000000000"
    print("[1/4] Sipariş kalemleri siliniyor...")
    client.table("order_items").delete().neq("id", dummy).execute()
    print("[2/4] Siparişler siliniyor...")
    client.table("orders").delete().neq("id", dummy).execute()
    print("[3/4] Adresler siliniyor...")
    client.table("customer_addresses").delete().neq("id", dummy).execute()
    print("[4/4] Müşteriler siliniyor...")
    client.table("customers").delete().neq("id", dummy).execute()
    print("      Silme tamamlandı.")


def import_from_excel():
    """Excel'den müşterileri toplu olarak ekle."""
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    print(f"[3/3] {len(rows)-1} müşteri ekleniyor...")

    client = get_client()
    inserted = 0
    skipped = 0
    batch_customers = []

    for row in rows[1:]:
        name = str(row[0]).strip() if row[0] else ""
        phone_raw = str(row[1]).strip() if row[1] else ""
        addr1 = str(row[2]).strip() if row[2] else ""
        addr2 = str(row[3]).strip() if row[3] else ""

        phone = normalize_phone(phone_raw)
        if not phone or not name:
            skipped += 1
            continue

        batch_customers.append({
            "name": name,
            "phone": phone,
            "addr1": addr1,
            "addr2": addr2,
        })

    # Tekrarlanan numaraları filtrele
    seen = set()
    unique_customers = []
    for c in batch_customers:
        if c["phone"] not in seen:
            seen.add(c["phone"])
            unique_customers.append(c)
        else:
            skipped += 1

    total = len(unique_customers)
    print(f"      Benzersiz: {total}, Atlanan: {skipped}")

    # Toplu ekleme
    for i in range(0, total, BATCH_SIZE):
        batch = unique_customers[i:i+BATCH_SIZE]

        # Müşterileri ekle
        cust_payload = [{"name": c["name"], "phone": c["phone"]} for c in batch]
        res = client.table("customers").insert(cust_payload).execute()

        if not res.data:
            print(f"      HATA: Batch {i}-{i+len(batch)} eklenemedi")
            continue

        # Adresleri ekle
        addr_payload = []
        for cust_data, cust_row in zip(res.data, batch):
            cust_id = cust_data["id"]
            if cust_row["addr1"]:
                addr_payload.append({
                    "customer_id": cust_id,
                    "title": "Adres 1",
                    "address_text": cust_row["addr1"],
                    "is_default": True,
                })
            if cust_row["addr2"]:
                addr_payload.append({
                    "customer_id": cust_id,
                    "title": "Adres 2",
                    "address_text": cust_row["addr2"],
                    "is_default": False,
                })

        if addr_payload:
            client.table("customer_addresses").insert(addr_payload).execute()

        inserted += len(batch)
        if inserted % 2000 == 0 or inserted == total:
            print(f"      İlerleme: {inserted}/{total}")

    print(f"\n✓ Tamamlandı: {inserted} müşteri eklendi.")


if __name__ == "__main__":
    delete_all_customers()
    import_from_excel()
