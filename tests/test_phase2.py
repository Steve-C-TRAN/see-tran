# tests/test_phase2.py
"""
Core model and route tests for the current domain model.
Covers: Agency, Vendor, Component, Product, Configuration, Suggestion.
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
def seed_data(app):
    """Seed a minimal set of related records for testing. Returns IDs to avoid detached instance errors."""
    with app.app_context():
        agency = Agency(name="Test Transit Agency", location="Portland, OR", short_name="tta")
        vendor = Vendor(name="Test Vendor Co", website="https://testvendor.example.com")
        fa = FunctionalArea(name="Operations", description="Day-to-day transit operations")
        db.session.add_all([agency, vendor, fa])
        db.session.flush()

        func = Function(name="Scheduling", functional_area_id=fa.id, criticality=Criticality.high)
        comp = Component(name="CAD/AVL", description="Computer-aided dispatch and automatic vehicle location")
        db.session.add_all([func, comp])
        db.session.flush()

        func.components.append(comp)

        product = Product(name="TestCAD Pro", vendor_id=vendor.id, lifecycle_stage=LifecycleStage.production)
        db.session.add(product)
        db.session.flush()

        pv = ProductVersion(product_id=product.id, version="3.1.0")
        db.session.add(pv)
        db.session.flush()

        config = Configuration(
            agency_id=agency.id,
            function_id=func.id,
            component_id=comp.id,
            status="Active",
        )
        db.session.add(config)
        db.session.flush()

        cp = ConfigurationProduct(
            configuration_id=config.id,
            product_id=product.id,
            product_version_id=pv.id,
        )
        db.session.add(cp)

        st = ServiceType(name="Fixed")
        db.session.add(st)
        db.session.flush()
        config.service_types.append(st)

        db.session.commit()

        return {
            "agency_id": agency.id,
            "vendor_id": vendor.id,
            "fa_id": fa.id,
            "func_id": func.id,
            "comp_id": comp.id,
            "product_id": product.id,
            "pv_id": pv.id,
            "config_id": config.id,
            "service_type_id": st.id,
        }


# =========================================================================
# Model tests
# =========================================================================

class TestModels:
    def test_agency_creation(self, app):
        with app.app_context():
            a = Agency(name="Metro Transit", location="Minneapolis, MN")
            db.session.add(a)
            db.session.commit()
            assert a.id is not None
            assert Agency.query.filter_by(name="Metro Transit").first() is not None

    def test_agency_unique_name(self, app):
        with app.app_context():
            db.session.add(Agency(name="UniqueAgency"))
            db.session.commit()
            db.session.add(Agency(name="UniqueAgency"))
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()

    def test_vendor_creation(self, app):
        with app.app_context():
            v = Vendor(name="Cubic", website="https://cubic.com")
            db.session.add(v)
            db.session.commit()
            assert v.id is not None

    def test_product_lifecycle(self, app):
        with app.app_context():
            v = Vendor(name="Acme")
            db.session.add(v)
            db.session.flush()
            p = Product(name="Widget", vendor_id=v.id, lifecycle_stage=LifecycleStage.pilot)
            db.session.add(p)
            db.session.commit()
            assert p.lifecycle_stage == LifecycleStage.pilot

    def test_product_version_unique_constraint(self, app):
        with app.app_context():
            v = Vendor(name="DupTest")
            db.session.add(v)
            db.session.flush()
            p = Product(name="DupProd", vendor_id=v.id)
            db.session.add(p)
            db.session.flush()
            db.session.add(ProductVersion(product_id=p.id, version="1.0"))
            db.session.commit()
            db.session.add(ProductVersion(product_id=p.id, version="1.0"))
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()

    def test_configuration_unique_constraint(self, app, seed_data):
        with app.app_context():
            dup = Configuration(
                agency_id=seed_data["agency_id"],
                function_id=seed_data["func_id"],
                component_id=seed_data["comp_id"],
            )
            db.session.add(dup)
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()

    def test_configuration_service_types(self, app, seed_data):
        with app.app_context():
            config = Configuration.query.first()
            assert len(config.service_types) == 1
            assert config.service_types[0].name == "Fixed"

    def test_configuration_products(self, app, seed_data):
        with app.app_context():
            config = Configuration.query.first()
            assert len(config.products) == 1
            cp = config.products[0]
            assert cp.product.name == "TestCAD Pro"
            assert cp.product_version.version == "3.1.0"

    def test_function_component_m2m(self, app, seed_data):
        with app.app_context():
            func = Function.query.filter_by(name="Scheduling").first()
            assert len(func.components) == 1
            assert func.components[0].name == "CAD/AVL"


# =========================================================================
# Suggestion model tests
# =========================================================================

class TestSuggestionModel:
    def test_create_suggestion(self, app, seed_data):
        with app.app_context():
            s = Suggestion(
                entity_type="agency",
                entity_id=seed_data["agency_id"],
                field="website",
                suggested_value="https://new-website.example.com",
                current_value=None,
                confidence=0.92,
            )
            db.session.add(s)
            db.session.commit()
            assert s.id is not None
            assert s.status == "pending"

    def test_suggestion_status_filter(self, app, seed_data):
        with app.app_context():
            aid = seed_data["agency_id"]
            for i, status in enumerate(["pending", "pending", "accepted", "rejected"]):
                s = Suggestion(
                    entity_type="agency", entity_id=aid,
                    field=f"field_{i}", suggested_value=f"val_{i}",
                    status=status,
                )
                db.session.add(s)
            db.session.commit()
            assert Suggestion.query.filter_by(status="pending").count() == 2
            assert Suggestion.query.filter_by(status="accepted").count() == 1
            assert Suggestion.query.filter_by(status="rejected").count() == 1


# =========================================================================
# Route tests — internal API (existing HTMX/fragment routes)
# =========================================================================

class TestInternalRoutes:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_index_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_count_endpoints(self, client, seed_data):
        for entity in ("agencies", "vendors", "components", "configurations", "products"):
            resp = client.get(f"/api/count/{entity}")
            assert resp.status_code == 200, f"/api/count/{entity} returned {resp.status_code}"

    def test_agencies_list_fragment(self, client, seed_data):
        resp = client.get("/api/agencies/list")
        assert resp.status_code == 200

    def test_vendors_list_fragment(self, client, seed_data):
        resp = client.get("/api/vendors/list")
        assert resp.status_code == 200

    def test_components_list_fragment(self, client, seed_data):
        resp = client.get("/api/components/list")
        assert resp.status_code == 200

    def test_vendor_stats(self, client, seed_data):
        resp = client.get("/api/vendors/stats")
        assert resp.status_code == 200

    def test_agency_details_fragment(self, client, seed_data):
        with client.application.app_context():
            a = Agency.query.first()
        resp = client.get(f"/api/agencies/{a.id}/details")
        assert resp.status_code == 200

    def test_component_details_fragment(self, client, seed_data):
        with client.application.app_context():
            c = Component.query.first()
        resp = client.get(f"/api/components/{c.id}/details")
        assert resp.status_code == 200

    def test_configurations_list_requires_login(self, client, seed_data):
        resp = client.get("/api/configurations/list")
        assert resp.status_code == 401  # API returns 401 when not logged in

    def test_configurations_page_requires_login(self, client, seed_data):
        resp = client.get("/configurations")
        assert resp.status_code == 302  # page redirects to login
