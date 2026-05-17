import requests
import uuid

BASE_URL = "http://localhost:5000/rest/v1"
API_KEY = "sb_publishable_PVh2wYSRzx9rjoxFPDAn-Q_oernzdtT"
HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def test_customer_management_crud_operations():
    # Helper function to create customer
    def create_customer(name, phone, email=None, notes=None, is_guest=False):
        payload = {
            "name": name,
            "phone": phone,
            "email": email,
            "notes": notes,
            "is_guest": is_guest
        }
        response = requests.post(f"{BASE_URL}/customers", json=payload, headers=HEADERS, timeout=30)
        return response

    # Helper function to delete customer by id
    def delete_customer(customer_id):
        response = requests.delete(f"{BASE_URL}/customers?id=eq.{customer_id}", headers=HEADERS, timeout=30)
        return response

    # Helper function to get customer by id
    def get_customer(customer_id):
        response = requests.get(f"{BASE_URL}/customers?id=eq.{customer_id}", headers=HEADERS, timeout=30)
        return response

    # Helper function to patch/update customer by id
    def update_customer(customer_id, name=None, phone=None):
        data = {}
        if name is not None:
            data["name"] = name
        if phone is not None:
            data["phone"] = phone
        response = requests.patch(f"{BASE_URL}/customers?id=eq.{customer_id}", json=data, headers=HEADERS, timeout=30)
        return response

    # Helper function to list customers with optional params
    def list_customers(params=None):
        response = requests.get(f"{BASE_URL}/customers", headers=HEADERS, timeout=30, params=params)
        return response

    # Step 1: Create new customer with valid data
    unique_phone = f"+1555{str(uuid.uuid4().int)[:8]}"
    create_resp = create_customer(name="Test User", phone=unique_phone, email="testuser@example.com", notes="Initial notes", is_guest=False)
    assert create_resp.status_code == 201, f"Unexpected status code creating customer: {create_resp.status_code}"
    created_customer = create_resp.json()
    assert "id" in created_customer, "Created customer response missing 'id'"
    customer_id = created_customer["id"]

    try:
        # Step 2: Attempt to create a customer with duplicate phone number, expect 409 Conflict
        duplicate_resp = create_customer(name="Duplicate User", phone=unique_phone, email="dup@example.com", notes="", is_guest=False)
        assert duplicate_resp.status_code == 409, f"Expected 409 for duplicate phone, got {duplicate_resp.status_code}"

        # Step 3: Update customer details (name and phone)
        new_phone = f"+1666{str(uuid.uuid4().int)[:8]}"
        update_resp = update_customer(customer_id, name="Updated Test User", phone=new_phone)
        assert update_resp.status_code == 200, f"Unexpected status code updating customer: {update_resp.status_code}"
        updated_customer = update_resp.json()
        assert updated_customer.get("name") == "Updated Test User", "Customer name not updated correctly"
        assert updated_customer.get("phone") == new_phone, "Customer phone not updated correctly"

        # Step 4: Retrieve customer by ID and verify updated data
        get_resp = get_customer(customer_id)
        assert get_resp.status_code == 200, f"Unexpected status code retrieving customer: {get_resp.status_code}"
        retrieved_customer = get_resp.json()
        # When filtering by id=eq.{id}, Supabase returns a list containing one item if found
        if isinstance(retrieved_customer, list):
            assert len(retrieved_customer) == 1, "Expected one customer in list"
            retrieved_customer = retrieved_customer[0]
        assert retrieved_customer.get("id") == customer_id, "Retrieved customer id mismatch"
        assert retrieved_customer.get("name") == "Updated Test User", "Retrieved customer name mismatch"
        assert retrieved_customer.get("phone") == new_phone, "Retrieved customer phone mismatch"

        # Step 5: List customers with search parameter - filter by name like 'Updated Test User'
        params = {"name": "ilike.%Updated Test User%"}
        list_resp = list_customers(params=params)
        assert list_resp.status_code == 200, f"Unexpected status code listing customers: {list_resp.status_code}"
        customers_list = list_resp.json()
        assert any(c.get("id") == customer_id for c in customers_list), "Updated customer not found in list with search params"

        # Step 6: Delete customer with no blocking dependencies
        del_resp = delete_customer(customer_id)
        assert del_resp.status_code == 200, f"Unexpected status code deleting customer: {del_resp.status_code}"

        # Step 7: Confirm deletion - customer should no longer exist
        confirm_resp = get_customer(customer_id)
        assert confirm_resp.status_code == 200, f"Unexpected status code retrieving after deletion: {confirm_resp.status_code}"
        confirm_json = confirm_resp.json()
        # After deletion, Supabase returns an empty list when no record found
        assert isinstance(confirm_json, list) and len(confirm_json) == 0, "Deleted customer still found in database"

    finally:
        # Cleanup if customer still exists (e.g. test failed before deletion)
        try:
            cleanup_resp = get_customer(customer_id)
            if cleanup_resp.status_code == 200 and cleanup_resp.json():
                delete_customer(customer_id)
        except Exception:
            pass

test_customer_management_crud_operations()