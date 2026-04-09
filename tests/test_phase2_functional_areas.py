# tests/test_phase2_functional_areas.py
"""
Functional Area and Function CRUD tests.
"""

import pytest
from app import create_app, db
from app.models.tran import FunctionalArea, Function, Component, Criticality


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
def seed_fa(app):
    """Seed functional areas with functions and components."""
    with app.app_context():
        fa1 = FunctionalArea(name="Operations", description="Day-to-day ops")
        fa2 = FunctionalArea(name="Finance", description="Financial management")
        db.session.add_all([fa1, fa2])
        db.session.flush()

        f1 = Function(name="Scheduling", functional_area_id=fa1.id, criticality=Criticality.high)
        f2 = Function(name="Dispatching", functional_area_id=fa1.id, criticality=Criticality.high)
        f3 = Function(name="Budgeting", functional_area_id=fa2.id, criticality=Criticality.medium)
        db.session.add_all([f1, f2, f3])
        db.session.flush()

        comp = Component(name="CAD/AVL", description="Computer-aided dispatch")
        db.session.add(comp)
        db.session.flush()
        f1.components.append(comp)
        f2.components.append(comp)

        db.session.commit()
        return {"fa1": fa1, "fa2": fa2, "f1": f1, "f2": f2, "f3": f3, "comp": comp}


# =========================================================================
# Model tests
# =========================================================================

class TestFunctionalAreaModel:
    def test_create_functional_area(self, app):
        with app.app_context():
            fa = FunctionalArea(name="Maintenance", description="Asset maintenance")
            db.session.add(fa)
            db.session.commit()
            assert fa.id is not None
            assert FunctionalArea.query.count() == 1

    def test_functional_area_has_functions(self, app, seed_fa):
        with app.app_context():
            fa = FunctionalArea.query.filter_by(name="Operations").first()
            assert len(fa.functions) == 2
            names = {f.name for f in fa.functions}
            assert names == {"Scheduling", "Dispatching"}

    def test_function_criticality(self, app, seed_fa):
        with app.app_context():
            f = Function.query.filter_by(name="Budgeting").first()
            assert f.criticality == Criticality.medium

    def test_function_component_relationship(self, app, seed_fa):
        with app.app_context():
            comp = Component.query.filter_by(name="CAD/AVL").first()
            assert len(comp.functions) == 2

    def test_cascade_delete(self, app, seed_fa):
        with app.app_context():
            fa = FunctionalArea.query.filter_by(name="Finance").first()
            db.session.delete(fa)
            db.session.commit()
            assert Function.query.filter_by(name="Budgeting").first() is None


# =========================================================================
# Route tests
# =========================================================================

class TestFunctionalAreaRoutes:
    def test_functional_areas_page(self, client, seed_fa):
        resp = client.get("/functional-areas")
        assert resp.status_code == 200

    def test_functional_areas_list_api(self, client, seed_fa):
        resp = client.get("/api/functional-areas/list")
        assert resp.status_code == 200

    def test_functional_area_details(self, client, seed_fa):
        with client.application.app_context():
            fa = FunctionalArea.query.first()
        resp = client.get(f"/api/functional-areas/{fa.id}/details")
        assert resp.status_code == 200

    def test_functional_area_filter_options(self, client, seed_fa):
        resp = client.get("/api/filter-options/functional-areas")
        assert resp.status_code == 200

    def test_count_functional_areas(self, client, seed_fa):
        resp = client.get("/api/count/functional-areas")
        assert resp.status_code == 200

    def test_functional_areas_print(self, client, seed_fa):
        resp = client.get("/functional-areas/print")
        assert resp.status_code == 200

    def test_components_page(self, client, seed_fa):
        resp = client.get("/components")
        assert resp.status_code == 200

    def test_components_list(self, client, seed_fa):
        resp = client.get("/api/components/list")
        assert resp.status_code == 200
