import requests
import uuid

BASE_URL = "http://localhost:5000"
API_KEY_URL = "https://xgvlgmikxchpttydtelb.supabase.co"
API_KEY_VALUE = "sb_publishable_PVh2wYSRzx9rjoxFPDAn-Q_oernzdtT"
HEADERS = {
    "apikey": API_KEY_VALUE,
    "Authorization": f"Bearer {API_KEY_VALUE}",
    "Content-Type": "application/json",
}


def test_courier_management_crud():
    session = requests.Session()
    session.headers.update(HEADERS)
    timeout = 30

    courier_data = {
        "name": "Test Courier",
        "phone": f"+90{uuid.uuid4().int>>64:010d}",  # unique phone for test (format approx)
        "is_active": True
    }

    courier_id = None

    try:
        # Create Courier
        resp = session.post(
            f"{BASE_URL}/rest/v1/couriers",
            json=courier_data,
            timeout=timeout,
        )
        assert resp.status_code == 201, f"Create courier failed: {resp.status_code} {resp.text}"
        created_courier = resp.json()
        assert isinstance(created_courier, dict), "Expected an object response"
        courier_id = created_courier.get("id")
        assert courier_id is not None, "Created courier ID missing"
        assert created_courier["name"] == courier_data["name"]
        assert created_courier["phone"] == courier_data["phone"]
        assert created_courier["is_active"] == courier_data["is_active"]

        # List all couriers
        resp = session.get(f"{BASE_URL}/rest/v1/couriers", timeout=timeout)
        assert resp.status_code == 200, f"List couriers failed: {resp.status_code} {resp.text}"
        couriers_list = resp.json()
        assert isinstance(couriers_list, list), "Couriers list response is not a list"
        # Verify created courier in list by id
        assert any(c.get("id") == courier_id for c in couriers_list), "Created courier not in list"

        # Get courier by ID using PostgREST style param
        resp = session.get(f"{BASE_URL}/rest/v1/couriers?id=eq.{courier_id}", timeout=timeout)
        assert resp.status_code == 200, f"Get courier by ID failed: {resp.status_code} {resp.text}"
        courier_by_id = resp.json()
        assert isinstance(courier_by_id, list), "Expected array response for get by ID"
        assert len(courier_by_id) == 1, "Expected exactly one courier for given ID"
        courier_by_id = courier_by_id[0]
        assert courier_by_id["id"] == courier_id
        assert courier_by_id["name"] == courier_data["name"]
        assert courier_by_id["phone"] == courier_data["phone"]
        assert courier_by_id["is_active"] == courier_data["is_active"]

        # Update courier name
        updated_name = "Updated Courier Name"
        patch_data = {"name": updated_name}
        resp = session.patch(
            f"{BASE_URL}/rest/v1/couriers?id=eq.{courier_id}",
            json=patch_data,
            timeout=timeout,
        )
        assert resp.status_code == 200, f"Update courier failed: {resp.status_code} {resp.text}"
        updated_courier = resp.json()
        assert isinstance(updated_courier, dict), "Expected object response on update"
        assert updated_courier["id"] == courier_id
        assert updated_courier["name"] == updated_name

        # Delete courier
        resp = session.delete(f"{BASE_URL}/rest/v1/couriers?id=eq.{courier_id}", timeout=timeout)
        assert resp.status_code == 200, f"Delete courier failed: {resp.status_code} {resp.text}"
        # Confirm deletion by GET returning empty array
        resp = session.get(f"{BASE_URL}/rest/v1/couriers?id=eq.{courier_id}", timeout=timeout)
        assert resp.status_code == 200, f"Get courier after delete failed: {resp.status_code} {resp.text}"
        deleted_check = resp.json()
        assert isinstance(deleted_check, list), "Expected array response after delete"
        assert len(deleted_check) == 0, "Courier record still exists after deletion"

    finally:
        # Cleanup if courier still exists (in case of test failure)
        if courier_id is not None:
            try:
                resp = session.delete(f"{BASE_URL}/rest/v1/couriers?id=eq.{courier_id}", timeout=timeout)
            except Exception:
                pass


test_courier_management_crud()
