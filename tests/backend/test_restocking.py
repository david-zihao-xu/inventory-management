"""
Tests for the Restocking candidates endpoint and order creation (POST /api/orders).
"""
import pytest


class TestRestockingCandidatesEndpoint:
    """Test suite for the /api/restocking/candidates endpoint."""

    def test_get_all_candidates(self, client):
        """Test getting all restock candidates."""
        response = client.get("/api/restocking/candidates")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        for field in (
            "item_sku", "item_name", "current_demand", "forecasted_demand",
            "gap", "unit_cost", "gap_cost", "trend", "period",
        ):
            assert field in first

    def test_candidates_only_positive_gap(self, client):
        """Candidates must only include items with a positive demand gap."""
        response = client.get("/api/restocking/candidates")
        data = response.json()

        for c in data:
            assert c["gap"] > 0
            # gap should equal forecasted - current
            assert c["gap"] == c["forecasted_demand"] - c["current_demand"]

    def test_candidates_sorted_by_gap_desc(self, client):
        """Candidates must be sorted by gap descending (highest priority first)."""
        response = client.get("/api/restocking/candidates")
        data = response.json()

        gaps = [c["gap"] for c in data]
        assert gaps == sorted(gaps, reverse=True)

    def test_candidate_gap_cost_calculation(self, client):
        """gap_cost must equal gap * unit_cost."""
        response = client.get("/api/restocking/candidates")
        data = response.json()

        for c in data:
            assert isinstance(c["gap"], int)
            assert isinstance(c["unit_cost"], (int, float))
            assert abs(c["gap_cost"] - c["gap"] * c["unit_cost"]) < 0.01

    def test_decreasing_demand_item_excluded(self, client):
        """An item whose forecast is below current demand has no gap and is excluded."""
        response = client.get("/api/restocking/candidates")
        skus = {c["item_sku"] for c in response.json()}
        # MTR-304 has forecasted_demand (35) < current_demand (50) -> excluded
        assert "MTR-304" not in skus

    def test_demand_endpoint_unaffected(self, client):
        """The /api/demand response_model must not leak the added unit_cost field."""
        response = client.get("/api/demand")
        assert response.status_code == 200
        for item in response.json():
            assert "unit_cost" not in item


class TestCreateOrderEndpoint:
    """Test suite for POST /api/orders (restock order submission)."""

    def test_create_order_success(self, client):
        """Submitting a valid order returns 201 with a Submitted restock order."""
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A",
                 "quantity": 100, "unit_price": 45.0},
                {"sku": "FLT-405", "name": "Oil Filter Cartridge",
                 "quantity": 50, "unit_price": 8.5},
            ]
        }
        response = client.post("/api/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["source"] == "restock"
        assert order["customer"] == "Internal Restock"
        assert order["lead_time_days"] == 14
        assert order["order_number"].startswith("RST-")
        assert len(order["items"]) == 2

    def test_create_order_total_value(self, client):
        """total_value must equal the sum of quantity * unit_price across items."""
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A",
                 "quantity": 100, "unit_price": 45.0},
                {"sku": "FLT-405", "name": "Oil Filter Cartridge",
                 "quantity": 50, "unit_price": 8.5},
            ]
        }
        response = client.post("/api/orders", json=payload)
        order = response.json()

        expected = 100 * 45.0 + 50 * 8.5
        assert abs(order["total_value"] - expected) < 0.01

    def test_create_order_lead_time_in_dates(self, client):
        """expected_delivery must be lead_time_days after order_date."""
        from datetime import datetime

        payload = {
            "items": [
                {"sku": "GSK-203", "name": "High-Temperature Gasket",
                 "quantity": 10, "unit_price": 12.75},
            ]
        }
        response = client.post("/api/orders", json=payload)
        order = response.json()

        order_date = datetime.fromisoformat(order["order_date"])
        expected_delivery = datetime.fromisoformat(order["expected_delivery"])
        assert (expected_delivery - order_date).days == order["lead_time_days"]

    def test_create_order_custom_lead_time(self, client):
        """A custom lead_time_days is honored."""
        payload = {
            "items": [
                {"sku": "GSK-203", "name": "High-Temperature Gasket",
                 "quantity": 10, "unit_price": 12.75},
            ],
            "lead_time_days": 21,
        }
        response = client.post("/api/orders", json=payload)
        assert response.status_code == 201
        assert response.json()["lead_time_days"] == 21

    def test_create_order_appears_in_orders_list(self, client):
        """A submitted order is retrievable from GET /api/orders."""
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A",
                 "quantity": 5, "unit_price": 45.0},
            ]
        }
        created = client.post("/api/orders", json=payload).json()

        all_orders = client.get("/api/orders").json()
        order_numbers = [o["order_number"] for o in all_orders]
        assert created["order_number"] in order_numbers

    def test_create_order_empty_items_rejected(self, client):
        """An order with no items returns 400."""
        response = client.post("/api/orders", json={"items": []})
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_order_invalid_payload_rejected(self, client):
        """A malformed item (missing required fields) returns 422."""
        response = client.post(
            "/api/orders",
            json={"items": [{"sku": "WDG-001"}]},
        )
        assert response.status_code == 422

    def test_order_number_uses_current_year(self, client):
        """The restock order_number must reflect the actual current year, not a hardcoded one."""
        from datetime import datetime

        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A",
                 "quantity": 1, "unit_price": 45.0},
            ]
        }
        order = client.post("/api/orders", json=payload).json()
        # order_date and order_number must agree on the year
        order_year = datetime.fromisoformat(order["order_date"]).year
        assert order["order_number"].startswith(f"RST-{order_year}-")


class TestRestockRevenueExclusion:
    """Restock orders are internal purchase spend and must not be counted as revenue."""

    def _place_restock_order(self, client):
        """Place a restock order and return its total_value (the restock cost)."""
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A",
                 "quantity": 100, "unit_price": 45.0},
            ]
        }
        created = client.post("/api/orders", json=payload).json()
        return created["total_value"]

    def test_restock_excluded_from_dashboard_revenue(self, client):
        """A placed restock order must not inflate dashboard total_orders_value (revenue)."""
        before = client.get("/api/dashboard/summary").json()["total_orders_value"]
        self._place_restock_order(client)
        after = client.get("/api/dashboard/summary").json()["total_orders_value"]
        # Revenue is unchanged: the restock cost is excluded.
        assert abs(after - before) < 0.01

    def test_restock_excluded_from_monthly_trends(self, client):
        """A placed restock order must not add revenue or a spurious bucket to monthly-trends."""
        before = client.get("/api/reports/monthly-trends").json()
        before_revenue = sum(m["revenue"] for m in before)
        before_months = {m["month"] for m in before}

        self._place_restock_order(client)

        after = client.get("/api/reports/monthly-trends").json()
        after_revenue = sum(m["revenue"] for m in after)
        after_months = {m["month"] for m in after}

        # No revenue added and no new month bucket introduced by the restock order.
        assert abs(after_revenue - before_revenue) < 0.01
        assert after_months == before_months

    def test_restock_excluded_from_quarterly_revenue(self, client):
        """A placed restock order must not change quarterly total_revenue."""
        before = {q["quarter"]: q["total_revenue"] for q in client.get("/api/reports/quarterly").json()}
        self._place_restock_order(client)
        after = {q["quarter"]: q["total_revenue"] for q in client.get("/api/reports/quarterly").json()}
        assert after == before
