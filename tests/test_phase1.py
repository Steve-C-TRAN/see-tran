# tests/test_phase1.py
"""
Foundation tests: app factory, error helpers, health check, auth decorators.
"""

import pytest
from app import create_app, db
from app.models.tran import Agency, Vendor, FunctionalArea


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# =========================================================================
# App factory
# =========================================================================

class TestAppFactory:
    def test_app_creates(self, app):
        assert app is not None
        assert app.config["TESTING"] is True

    def test_db_tables_created(self, app):
        with app.app_context():
            # Smoke test — query should not raise
            assert Agency.query.count() == 0
            assert Vendor.query.count() == 0


# =========================================================================
# Error helpers
# =========================================================================

class TestErrorHelpers:
    def test_api_ok(self, app):
        with app.app_context():
            from app.utils.errors import api_ok
            resp, status = api_ok({"foo": "bar"})
            data = resp.get_json()
            assert status == 200
            assert data["ok"] is True
            assert data["data"]["foo"] == "bar"

    def test_api_error(self, app):
        with app.app_context():
            from app.utils.errors import api_error
            resp, status = api_error("bad request", 400)
            data = resp.get_json()
            assert status == 400
            assert data["ok"] is False
            assert data["error"] == "bad request"

    def test_api_validation_error(self, app):
        with app.app_context():
            from app.utils.errors import api_validation_error
            resp, status = api_validation_error({"name": "required"})
            data = resp.get_json()
            assert status == 422
            assert data["fields"]["name"] == "required"

    def test_html_fragments(self, app):
        with app.app_context():
            from app.utils.errors import html_error_fragment, html_success_fragment
            err = html_error_fragment("something broke")
            assert "something broke" in err
            assert "bg-red-900/20" in err

            ok = html_success_fragment("all good")
            assert "all good" in ok
            assert "bg-green-900/20" in ok


# =========================================================================
# Core routes
# =========================================================================

class TestCoreRoutes:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_index(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_count_agencies(self, client):
        resp = client.get("/api/count/agencies")
        assert resp.status_code == 200

    def test_count_vendors(self, client):
        resp = client.get("/api/count/vendors")
        assert resp.status_code == 200

    def test_count_components(self, client):
        resp = client.get("/api/count/components")
        assert resp.status_code == 200

    def test_agencies_list(self, client):
        resp = client.get("/api/agencies/list")
        assert resp.status_code == 200

    def test_vendors_list(self, client):
        resp = client.get("/api/vendors/list")
        assert resp.status_code == 200

    def test_components_list(self, client):
        resp = client.get("/api/components/list")
        assert resp.status_code == 200

    def test_functional_areas_page(self, client):
        resp = client.get("/functional-areas")
        assert resp.status_code == 200

    def test_vendors_page(self, client):
        resp = client.get("/vendors")
        assert resp.status_code == 200

    def test_components_page(self, client):
        resp = client.get("/components")
        assert resp.status_code == 200

    def test_configurations_page_requires_login(self, client):
        resp = client.get("/configurations")
        assert resp.status_code == 302  # redirects to login

    def test_products_page_requires_login(self, client):
        resp = client.get("/products")
        assert resp.status_code == 302  # redirects to login

    def test_docs_page(self, client):
        resp = client.get("/docs")
        # May redirect to login if protected
        assert resp.status_code in (200, 302)
