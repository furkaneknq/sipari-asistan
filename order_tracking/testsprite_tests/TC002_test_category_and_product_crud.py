import requests
import uuid

BASE_URL = "http://localhost:5000"
API_KEY = "sb_publishable_PVh2wYSRzx9rjoxFPDAn-Q_oernzdtT"
HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def test_category_and_product_crud():
    category_id = None
    product_id = None
    try:
        # 1. Create a category
        category_payload = {
            "name": "Test Category",
            "color": "#123456",
            "sort_order": 1
        }
        r = requests.post(
            f"{BASE_URL}/rest/v1/categories",
            json=category_payload,
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 201, f"Expected 201 for category creation, got {r.status_code}"
        category = r.json()
        assert isinstance(category, dict), "Category creation response is not an object"
        assert "id" in category, "Created category has no ID"
        category_id = category["id"]

        # 2. Create a product linked to that category
        product_payload = {
            "name": "Test Product",
            "price": 10.5,
            "unit": "pcs",
            "category_id": category_id,
            "sort_order": 1
        }
        r = requests.post(
            f"{BASE_URL}/rest/v1/products",
            json=product_payload,
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 201, f"Expected 201 for product creation, got {r.status_code}"
        product = r.json()
        assert isinstance(product, dict), "Product creation response is not an object"
        assert "id" in product, "Created product has no ID"
        product_id = product["id"]

        # 3. List products filtered by product id
        r = requests.get(
            f"{BASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 200, f"Expected 200 for product get by id, got {r.status_code}"
        products = r.json()
        assert isinstance(products, list), "Response for product get by id is not a list"
        assert any(p["id"] == product_id for p in products), "Created product not found by id filter"

        r = requests.get(
            f"{BASE_URL}/rest/v1/products?category_id=eq.{category_id}",
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 200, f"Expected 200 for products filtered by category_id, got {r.status_code}"
        filtered_products = r.json()
        assert isinstance(filtered_products, list), "Filtered products response is not a list"
        assert any(p["id"] == product_id for p in filtered_products), "Created product not in filtered list"

        # 4. Update product price and name
        update_payload = {
            "price": 15.75,
            "name": "Updated Test Product"
        }
        r = requests.patch(
            f"{BASE_URL}/rest/v1/products?id=eq.{product_id}",
            json=update_payload,
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 200, f"Expected 200 for product update, got {r.status_code}"
        updated_products = r.json()
        assert isinstance(updated_products, list), "Product update response is not a list"
        assert len(updated_products) >= 1, "Product update response list is empty"
        updated_product = updated_products[0]
        assert updated_product["price"] == 15.75, "Product price not updated"
        assert updated_product["name"] == "Updated Test Product", "Product name not updated"

        # 5. Delete product
        r = requests.delete(
            f"{BASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 200, f"Expected 200 for product deletion, got {r.status_code}"

        # Verify product deletion
        r = requests.get(
            f"{BASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 200, f"Expected 200 for product get after deletion, got {r.status_code}"
        products_after_delete = r.json()
        assert isinstance(products_after_delete, list), "Response after product deletion is not a list"
        assert all(p["id"] != product_id for p in products_after_delete), "Deleted product still found"

        product_id = None  # Mark as deleted

    finally:
        # 6. Delete category
        if category_id:
            r = requests.delete(
                f"{BASE_URL}/rest/v1/categories?id=eq.{category_id}",
                headers=HEADERS,
                timeout=30,
            )
            assert r.status_code == 200, f"Expected 200 for category deletion, got {r.status_code}"

            # Verify category deletion
            r = requests.get(
                f"{BASE_URL}/rest/v1/categories?id=eq.{category_id}",
                headers=HEADERS,
                timeout=30,
            )
            assert r.status_code == 200, f"Expected 200 for category get after deletion, got {r.status_code}"
            categories_after_delete = r.json()
            assert isinstance(categories_after_delete, list), "Response after category deletion is not a list"
            assert all(c["id"] != category_id for c in categories_after_delete), "Deleted category still found"

test_category_and_product_crud()