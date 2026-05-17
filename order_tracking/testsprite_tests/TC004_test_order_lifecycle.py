import requests
import uuid
import datetime

BASE_URL = "http://localhost:5000"
API_KEY_NAME = "apikey"
API_KEY_VALUE = "sb_publishable_PVh2wYSRzx9rjoxFPDAn-Q_oernzdtT"
HEADERS = {
    API_KEY_NAME: API_KEY_VALUE,
    "Content-Type": "application/json",
    "Accept": "application/json"
}
TIMEOUT = 30


def test_order_lifecycle():
    customer_id = None
    category_id = None
    product_id = None
    courier_id = None
    address_id = None
    order_id = None

    try:
        # Step 1: Create a customer
        customer_payload = {
            "name": "Test Customer " + str(uuid.uuid4()),
            "phone": "+900000000000",
            "email": None,
            "notes": None,
            "is_guest": False
        }
        resp = requests.post(f"{BASE_URL}/rest/v1/customers", json=customer_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create customer failed: {resp.status_code} {resp.text}"
        customer_created = resp.json()
        customer_id = customer_created.get("id")
        assert customer_id, "customer_id not returned"

        # Step 2: Create a category for product
        category_payload = {
            "name": "Test Category " + str(uuid.uuid4()),
            "color": "#ff00ff",
            "sort_order": 1
        }
        resp = requests.post(f"{BASE_URL}/rest/v1/categories", json=category_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create category failed: {resp.status_code} {resp.text}"
        category = resp.json()
        category_id = category.get("id")
        assert category_id, "category_id not returned"

        # Step 3: Create a product linked to the category
        product_payload = {
            "name": "Test Product " + str(uuid.uuid4()),
            "price": 12.34,
            "unit": "pcs",
            "category_id": category_id,
            "sort_order": 1
        }
        resp = requests.post(f"{BASE_URL}/rest/v1/products", json=product_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create product failed: {resp.status_code} {resp.text}"
        product = resp.json()
        product_id = product.get("id")
        assert product_id, "product_id not returned"

        # Step 4: Create a courier
        courier_payload = {
            "name": "Test Courier " + str(uuid.uuid4()),
            "phone": "+901234567890",
            "password": None,
            "is_active": True
        }
        resp = requests.post(f"{BASE_URL}/rest/v1/couriers", json=courier_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create courier failed: {resp.status_code} {resp.text}"
        courier = resp.json()
        courier_id = courier.get("id")
        assert courier_id, "courier_id not returned"

        # Step 5: Create a customer address (required for order)
        address_payload = {
            "customer_id": customer_id,
            "title": "Test Address",
            "address_text": "123 Testing Lane",
            "latitude": 41.0,
            "longitude": 29.0,
            "is_default": True
        }
        resp = requests.post(f"{BASE_URL}/rest/v1/customer_addresses", json=address_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create customer address failed: {resp.status_code} {resp.text}"
        address = resp.json()
        address_id = address.get("id")
        assert address_id, "address_id not returned"

        # Step 6: Create an order for that customer with items
        order_payload = {
            "customer_id": customer_id,
            "address_id": address_id,
            "courier_id": None,
            "status": "new",
            "order_date": datetime.datetime.utcnow().isoformat()+"Z",
            "payment_method": "cash",
            "notes": None
        }
        resp = requests.post(f"{BASE_URL}/rest/v1/orders", json=order_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create order failed: {resp.status_code} {resp.text}"
        order = resp.json()
        order_id = order.get("id")
        assert order_id, "order_id not returned"

        # Step 7: Add order items to the order
        # Delete existing items if any (to ensure clean state)
        del_headers = HEADERS.copy()
        del_headers["Prefer"] = "return=minimal"
        del_resp = requests.delete(f"{BASE_URL}/rest/v1/order_items?order_id=eq.{order_id}", headers=del_headers, timeout=TIMEOUT)
        assert del_resp.status_code == 200, f"Delete existing order items failed: {del_resp.status_code} {del_resp.text}"

        order_items_payload = [{
            "order_id": order_id,
            "product_id": product_id,
            "quantity": 2,
            "unit": "pcs",
            "unit_price": 12.34
        }]
        resp = requests.post(f"{BASE_URL}/rest/v1/order_items", json=order_items_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 201, f"Create order items failed: {resp.status_code} {resp.text}"

        # Step 8: Verify order appears in order list
        resp = requests.get(f"{BASE_URL}/rest/v1/orders?id=eq.{order_id}", headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Get order failed: {resp.status_code} {resp.text}"
        orders = resp.json()
        assert any(o.get("id") == order_id for o in orders), "Order not found in list"

        # Step 9: Update order status from 'new' to 'preparing'
        patch_payload = {"status": "preparing"}
        resp = requests.patch(f"{BASE_URL}/rest/v1/orders?id=eq.{order_id}", json=patch_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Update order status to preparing failed: {resp.status_code} {resp.text}"
        updated_order = resp.json()
        assert updated_order.get("status") == "preparing", "Order status not updated to preparing"

        # Step 10: Update order status from 'preparing' to 'delivered'
        patch_payload = {"status": "delivered"}
        resp = requests.patch(f"{BASE_URL}/rest/v1/orders?id=eq.{order_id}", json=patch_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Update order status to delivered failed: {resp.status_code} {resp.text}"
        updated_order = resp.json()
        assert updated_order.get("status") == "delivered", "Order status not updated to delivered"

        # Step 11: Assign courier to the order
        patch_courier_payload = {"courier_id": courier_id}
        resp = requests.patch(f"{BASE_URL}/rest/v1/orders?id=eq.{order_id}", json=patch_courier_payload, headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Assign courier failed: {resp.status_code} {resp.text}"
        updated_order = resp.json()
        assert updated_order.get("courier_id") == courier_id, "Courier not assigned to order"

        # Step 12: Delete the order (which cascades to order_items)
        resp = requests.delete(f"{BASE_URL}/rest/v1/orders?id=eq.{order_id}", headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Delete order failed: {resp.status_code} {resp.text}"

        # Step 13: Verify order deleted
        resp = requests.get(f"{BASE_URL}/rest/v1/orders?id=eq.{order_id}", headers=HEADERS, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Get order after delete failed: {resp.status_code} {resp.text}"
        orders = resp.json()
        assert not any(o.get("id") == order_id for o in orders), "Order still exists after deletion"

    finally:
        # Cleanup created resources
        if order_id:
            try:
                requests.delete(f"{BASE_URL}/rest/v1/orders?id=eq.{order_id}", headers=HEADERS, timeout=TIMEOUT)
            except Exception:
                pass
        if courier_id:
            try:
                requests.delete(f"{BASE_URL}/rest/v1/couriers?id=eq.{courier_id}", headers=HEADERS, timeout=TIMEOUT)
            except Exception:
                pass
        if product_id:
            try:
                requests.delete(f"{BASE_URL}/rest/v1/products?id=eq.{product_id}", headers=HEADERS, timeout=TIMEOUT)
            except Exception:
                pass
        if category_id:
            try:
                requests.delete(f"{BASE_URL}/rest/v1/categories?id=eq.{category_id}", headers=HEADERS, timeout=TIMEOUT)
            except Exception:
                pass
        if address_id:
            try:
                requests.delete(f"{BASE_URL}/rest/v1/customer_addresses?id=eq.{address_id}", headers=HEADERS, timeout=TIMEOUT)
            except Exception:
                pass
        if customer_id:
            try:
                requests.delete(f"{BASE_URL}/rest/v1/customers?id=eq.{customer_id}", headers=HEADERS, timeout=TIMEOUT)
            except Exception:
                pass

test_order_lifecycle()
