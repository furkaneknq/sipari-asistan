import requests
import uuid

BASE_URL = "http://localhost:5000"
API_KEY = "sb_publishable_PVh2wYSRzx9rjoxFPDAn-Q_oernzdtT"
HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
TIMEOUT = 30


def test_customer_address_management():
    customer_id = None
    address_id = None

    # Create customer
    try:
        customer_payload = {
            "name": "Test Customer " + str(uuid.uuid4()),
            "phone": "5551234567",
            "email": None,
            "notes": None,
            "is_guest": False
        }
        r = requests.post(f"{BASE_URL}/rest/v1/customers", json=customer_payload, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 201, f"Create customer failed: {r.status_code} {r.text}"
        customer = r.json()
        assert "id" in customer and customer["id"], "Customer id missing in response"
        customer_id = customer["id"]

        # Add an address
        address_payload = {
            "customer_id": customer_id,
            "title": "Home",
            "address_text": "123 Testing Lane, Testville",
            "latitude": 40.7128,
            "longitude": -74.006,
            "is_default": True
        }
        r = requests.post(f"{BASE_URL}/rest/v1/customer_addresses", json=address_payload, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 201, f"Create address failed: {r.status_code} {r.text}"
        address = r.json()
        assert "id" in address and address["id"], "Address id missing in response"
        address_id = address["id"]
        assert address["customer_id"] == customer_id
        assert address["title"] == "Home"
        assert address["is_default"] is True

        # List addresses for customer
        r = requests.get(f"{BASE_URL}/rest/v1/customer_addresses?customer_id=eq.{customer_id}",
                         headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 200, f"List addresses failed: {r.status_code} {r.text}"
        addresses_list = r.json()
        assert any(addr["id"] == address_id for addr in addresses_list), "Created address not found in list"

        # Update address text and set as default (even if already default)
        updated_address_text = "456 Updated Lane, Testville"
        patch_payload = {
            "address_text": updated_address_text,
            "is_default": True
        }
        r = requests.patch(f"{BASE_URL}/rest/v1/customer_addresses?id=eq.{address_id}",
                           json=patch_payload, headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 200, f"Update address failed: {r.status_code} {r.text}"
        updated_address = r.json()
        assert updated_address["address_text"] == updated_address_text
        assert updated_address["is_default"] is True

        # Delete address
        r = requests.delete(f"{BASE_URL}/rest/v1/customer_addresses?id=eq.{address_id}",
                            headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 200, f"Delete address failed: {r.status_code} {r.text}"

        # Verify address deleted by listing addresses again
        r = requests.get(f"{BASE_URL}/rest/v1/customer_addresses?customer_id=eq.{customer_id}",
                         headers=HEADERS, timeout=TIMEOUT)
        assert r.status_code == 200, f"List addresses after delete failed: {r.status_code} {r.text}"
        addresses_after_delete = r.json()
        assert all(addr["id"] != address_id for addr in addresses_after_delete), "Deleted address still found in list"

    finally:
        # Clean up: delete customer if created
        if customer_id:
            r = requests.delete(f"{BASE_URL}/rest/v1/customers?id=eq.{customer_id}",
                                headers=HEADERS, timeout=TIMEOUT)
            # Delete may fail if dependencies exist; ignore assertion for cleanup
            if r.status_code != 200:
                pass

test_customer_address_management()