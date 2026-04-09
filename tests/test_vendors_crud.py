# tests/test_vendors_crud.py
"""
Vendor CRUD and Public API v1 tests.
"""

import pytest
from app import create_app, db
from app.models.tran import (
    Agency, Vendor, Component, Product, ProductVersion,
    FunctionalArea, Function, Configuration, ConfigurationProduct,
    ServiceType, Suggestion, Criticality, LifecycleStage,
)


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


@pytest.fixture
def seed_all(app):
    """Seed a full dataset for API testing."""
    with app.app_context():
        # Agencies
        a1 = Agency(name="Metro Transit", location="Portland, OR", short_name="metro", description="Portland metro area transit")
        a2 = Agency(name="Valley Transit", location="Boise, ID", short_name="valley")
        db.session.add_all([a1, a2])
        db.session.flush()

        # Vendors
        v1 = Vendor(name="Clever Devices", website="https://cleverdevices.com", description="Transit technology solutions")
        v2 = Vendor(name="Trapeze Group", website="https://trapezegroup.com", description="Fleet management software")
        db.session.add_all([v1, v2])
        db.session.flush()

        # Products
        p1 = Product(name="CleverCAD", vendor_id=v1.id, description="CAD/AVL system", lifecycle_stage=LifecycleStage.production)
        p2 = Product(name="Trapeze FX", vendor_id=v2.id, description="Fleet management", lifecycle_stage=LifecycleStage.production)
        db.session.add_all([p1, p2])
        db.session.flush()

        pv1 = ProductVersion(product_id=p1.id, version="5.2")
        pv2 = ProductVersion(product_id=p2.id, version="2024.1")
        db.session.add_all([pv1, pv2])
        db.session.flush()

        # Functional areas, functions, components
        fa = FunctionalArea(name="Operations", description="Transit operations")
        db.session.add(fa)
        db.session.flush()

        func = Function(name="Vehicle Tracking", functional_area_id=fa.id, criticality=Criticality.high)
        comp = Component(name="CAD/AVL", description="Dispatch and vehicle tracking", short_description="CAD/AVL system")
        db.session.add_all([func, comp])
        db.session.flush()

        func.components.append(comp)

        # Service type
        st = ServiceType(name="Fixed")
        db.session.add(st)
        db.session.flush()

        # Configurations
        config = Configuration(agency_id=a1.id, function_id=func.id, component_id=comp.id, status="Active")
        db.session.add(config)
        db.session.flush()

        cp = ConfigurationProduct(configuration_id=config.id, product_id=p1.id, product_version_id=pv1.id)
        db.session.add(cp)
        config.service_types.append(st)

        # Suggestions
        s1 = Suggestion(entity_type="agency", entity_id=a1.id, field="website",
                        suggested_value="https://metro-transit.example.com", confidence=0.95)
        s2 = Suggestion(entity_type="vendor", entity_id=v1.id, field="description",
                        suggested_value="Leading transit tech provider", current_value=v1.description, confidence=0.8)
        db.session.add_all([s1, s2])

        db.session.commit()
        return {
            "agencies": [a1, a2], "vendors": [v1, v2], "products": [p1, p2],
            "fa": fa, "func": func, "comp": comp, "config": config,
            "suggestions": [s1, s2],
        }


# =========================================================================
# Vendor route tests (internal HTMX API)
# =========================================================================

class TestVendorRoutes:
    def test_vendors_page(self, client, seed_all):
        resp = client.get("/vendors")
        assert resp.status_code == 200

    def test_vendors_list(self, client, seed_all):
        resp = client.get("/api/vendors/list")
        assert resp.status_code == 200

    def test_vendor_details(self, client, seed_all):
        with client.application.app_context():
            v = Vendor.query.first()
        resp = client.get(f"/api/vendors/{v.id}/details")
        assert resp.status_code == 200

    def test_vendor_stats(self, client, seed_all):
        resp = client.get("/api/vendors/stats")
        assert resp.status_code == 200

    def test_vendor_filter_options(self, client, seed_all):
        resp = client.get("/api/vendors/filter-options/functional-areas")
        assert resp.status_code == 200
        resp = client.get("/api/vendors/filter-options/agencies")
        assert resp.status_code == 200


# =========================================================================
# Public API v1 tests
# =========================================================================

class TestPublicAPIv1:
    # --- Agencies ---
    def test_list_agencies(self, client, seed_all):
        resp = client.get("/api/v1/agencies")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["data"]["items"]) == 2
        assert data["data"]["total"] == 2

    def test_list_agencies_search(self, client, seed_all):
        resp = client.get("/api/v1/agencies?search=Metro")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["name"] == "Metro Transit"

    def test_list_agencies_pagination(self, client, seed_all):
        resp = client.get("/api/v1/agencies?page=1&per_page=1")
        data = resp.get_json()
        assert data["data"]["per_page"] == 1
        assert data["data"]["pages"] == 2

    def test_get_agency_detail(self, client, seed_all):
        with client.application.app_context():
            a = Agency.query.filter_by(name="Metro Transit").first()
        resp = client.get(f"/api/v1/agencies/{a.id}")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["name"] == "Metro Transit"
        assert len(data["data"]["configurations"]) == 1
        config = data["data"]["configurations"][0]
        assert config["function"] == "Vehicle Tracking"
        assert config["component"] == "CAD/AVL"
        assert len(config["products"]) == 1

    def test_get_agency_not_found(self, client, seed_all):
        resp = client.get("/api/v1/agencies/9999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False

    # --- Vendors ---
    def test_list_vendors(self, client, seed_all):
        resp = client.get("/api/v1/vendors")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["data"]["items"]) == 2

    def test_get_vendor_detail(self, client, seed_all):
        with client.application.app_context():
            v = Vendor.query.filter_by(name="Clever Devices").first()
        resp = client.get(f"/api/v1/vendors/{v.id}")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["data"]["products"]) == 1
        assert data["data"]["products"][0]["name"] == "CleverCAD"

    # --- Components ---
    def test_list_components(self, client, seed_all):
        resp = client.get("/api/v1/components")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["data"]["items"]) == 1

    def test_get_component_detail(self, client, seed_all):
        with client.application.app_context():
            c = Component.query.first()
        resp = client.get(f"/api/v1/components/{c.id}")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["name"] == "CAD/AVL"
        assert "Vehicle Tracking" in data["data"]["function_names"]

    # --- Functions ---
    def test_list_functions(self, client, seed_all):
        resp = client.get("/api/v1/functions")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["data"]["items"]) == 1  # 1 functional area
        fa = data["data"]["items"][0]
        assert fa["name"] == "Operations"
        assert len(fa["functions"]) == 1

    def test_get_function_detail(self, client, seed_all):
        with client.application.app_context():
            f = Function.query.first()
        resp = client.get(f"/api/v1/functions/{f.id}")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["name"] == "Vehicle Tracking"
        assert data["data"]["functional_area"] == "Operations"

    # --- Configurations ---
    def test_list_configurations(self, client, seed_all):
        resp = client.get("/api/v1/configurations")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["data"]["items"]) == 1

    def test_list_configurations_filter_by_agency(self, client, seed_all):
        with client.application.app_context():
            a = Agency.query.filter_by(name="Metro Transit").first()
        resp = client.get(f"/api/v1/configurations?agency_id={a.id}")
        data = resp.get_json()
        assert len(data["data"]["items"]) == 1

    def test_list_configurations_filter_no_match(self, client, seed_all):
        resp = client.get("/api/v1/configurations?agency_id=9999")
        data = resp.get_json()
        assert len(data["data"]["items"]) == 0

    def test_get_configuration_detail(self, client, seed_all):
        with client.application.app_context():
            c = Configuration.query.first()
        resp = client.get(f"/api/v1/configurations/{c.id}")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["agency"] == "Metro Transit"
        assert data["data"]["service_types"] == ["Fixed"]
        assert len(data["data"]["products"]) == 1

    # --- Search ---
    def test_search_agencies(self, client, seed_all):
        resp = client.get("/api/v1/search?q=Metro&type=agency")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["total"] >= 1
        assert any(r["name"] == "Metro Transit" for r in data["data"]["items"])

    def test_search_vendors(self, client, seed_all):
        resp = client.get("/api/v1/search?q=Clever&type=vendor")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["total"] >= 1

    def test_search_products(self, client, seed_all):
        resp = client.get("/api/v1/search?q=CAD&type=product")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["total"] >= 1

    def test_search_components(self, client, seed_all):
        resp = client.get("/api/v1/search?q=dispatch&type=component")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["total"] >= 1

    def test_search_multi_type(self, client, seed_all):
        resp = client.get("/api/v1/search?q=CAD")
        data = resp.get_json()
        assert data["ok"] is True
        # Should find both the product and the component
        types = {r["type"] for r in data["data"]["items"]}
        assert len(types) >= 1

    def test_search_too_short(self, client, seed_all):
        resp = client.get("/api/v1/search?q=a")
        assert resp.status_code == 400

    def test_search_invalid_type(self, client, seed_all):
        resp = client.get("/api/v1/search?q=test&type=invalid")
        assert resp.status_code == 400

    def test_search_no_results(self, client, seed_all):
        resp = client.get("/api/v1/search?q=zzzzzzzzz")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["total"] == 0
