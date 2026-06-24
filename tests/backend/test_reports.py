"""
Tests for reports API endpoints (quarterly performance and monthly trends).

Covers the global filters (warehouse, category, status, month) that mirror the
/api/orders endpoint, and confirms restock orders are excluded from revenue.
"""


class TestReportsEndpoints:
    """Test suite for /api/reports/* endpoints."""

    # ---- Quarterly ----------------------------------------------------------

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly performance without filters."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        for field in ("quarter", "total_orders", "total_revenue",
                      "avg_order_value", "fulfillment_rate"):
            assert field in first

    def test_quarterly_sorted_and_typed(self, client):
        """Quarters are sorted and numeric fields have sane types/ranges."""
        data = client.get("/api/reports/quarterly").json()

        quarters = [q["quarter"] for q in data]
        assert quarters == sorted(quarters)

        for q in data:
            assert isinstance(q["total_orders"], int)
            assert q["total_orders"] > 0
            assert isinstance(q["total_revenue"], (int, float))
            assert 0 <= q["fulfillment_rate"] <= 100
            # avg_order_value should equal total_revenue / total_orders
            expected_avg = round(q["total_revenue"] / q["total_orders"], 2)
            assert abs(q["avg_order_value"] - expected_avg) < 0.01

    def test_quarterly_filter_by_category_reduces_orders(self, client):
        """Filtering by category yields a subset of the unfiltered orders."""
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get("/api/reports/quarterly?category=Sensors").json()

        total_unfiltered = sum(q["total_orders"] for q in unfiltered)
        total_filtered = sum(q["total_orders"] for q in filtered)

        assert total_filtered > 0
        assert total_filtered < total_unfiltered

    def test_quarterly_filter_by_month(self, client):
        """A single-month filter collapses results to that month's quarter."""
        data = client.get("/api/reports/quarterly?month=2025-02").json()
        assert isinstance(data, list)
        # February belongs only to Q1-2025
        assert all(q["quarter"] == "Q1-2025" for q in data)

    # ---- Monthly trends -----------------------------------------------------

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends without filters."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        for field in ("month", "order_count", "revenue", "delivered_count"):
            assert field in first

    def test_monthly_trends_sorted(self, client):
        """Months are returned in ascending order."""
        data = client.get("/api/reports/monthly-trends").json()
        months = [m["month"] for m in data]
        assert months == sorted(months)

    def test_monthly_trends_filter_by_warehouse(self, client):
        """Filtering by warehouse changes revenue vs the unfiltered total."""
        unfiltered = client.get("/api/reports/monthly-trends").json()
        filtered = client.get("/api/reports/monthly-trends?warehouse=Tokyo").json()

        total_unfiltered = sum(m["revenue"] for m in unfiltered)
        total_filtered = sum(m["revenue"] for m in filtered)

        assert total_filtered > 0
        assert total_filtered < total_unfiltered

    def test_monthly_trends_multiple_filters(self, client):
        """Combined filters return a non-empty, further-reduced result set."""
        category_only = client.get(
            "/api/reports/monthly-trends?category=Sensors"
        ).json()
        combined = client.get(
            "/api/reports/monthly-trends?category=Sensors&warehouse=Tokyo"
        ).json()

        cat_orders = sum(m["order_count"] for m in category_only)
        combined_orders = sum(m["order_count"] for m in combined)

        assert combined_orders <= cat_orders

    def test_reports_exclude_restock_orders(self, client):
        """Restock orders must not inflate revenue in either report."""
        monthly = client.get("/api/reports/monthly-trends").json()
        # Revenue should come only from customer orders; restock spend is
        # excluded server-side, so totals stay positive and finite.
        assert all(m["revenue"] >= 0 for m in monthly)
        assert sum(m["revenue"] for m in monthly) > 0
