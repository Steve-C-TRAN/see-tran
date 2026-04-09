# app/routes/api_v1.py
"""
Public read-only API v1 endpoints.

All endpoints are unauthenticated and return paginated JSON using the
standard envelope: {"ok": true, "data": {...}}.
"""

from flask import Blueprint, request
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app import db
from app.models.tran import (
    Agency, Vendor, Component, Product, ProductVersion,
    Function, FunctionalArea, Configuration, ConfigurationProduct,
    IntegrationPoint, Standard, ServiceType,
)
from app.utils.errors import api_ok, api_error

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------

def paginate(query):
    """Apply page/per_page from query string, return (items, meta)."""
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(
        request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int),
        MAX_PAGE_SIZE,
    )
    p = query.paginate(page=page, per_page=per_page, error_out=False)
    meta = {
        'page': p.page,
        'per_page': p.per_page,
        'total': p.total,
        'pages': p.pages,
    }
    return p.items, meta


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def serialize_agency(a):
    return {
        'id': a.id,
        'name': a.name,
        'short_name': a.short_name,
        'location': a.location,
        'description': a.description,
        'website': a.website,
        'ceo': a.ceo,
        'address_hq': a.address_hq,
        'phone_number': a.phone_number,
        'contact_email': a.contact_email,
        'contact_name': a.contact_name,
        'gtfs_feed_url': a.gtfs_feed_url,
    }


def serialize_agency_detail(a):
    data = serialize_agency(a)
    data['configurations'] = [
        {
            'id': c.id,
            'function': c.function.name if c.function else None,
            'component': c.component.name if c.component else None,
            'status': c.status,
            'deployment_date': c.deployment_date.isoformat() if c.deployment_date else None,
            'products': [
                {
                    'product': cp.product.name if cp.product else None,
                    'vendor': cp.product.vendor.name if cp.product and cp.product.vendor else None,
                    'version': cp.product_version.version if cp.product_version else None,
                }
                for cp in c.products
            ],
            'service_types': [st.name for st in c.service_types],
        }
        for c in a.configurations
    ]
    return data


def serialize_vendor(v):
    return {
        'id': v.id,
        'name': v.name,
        'short_name': v.short_name,
        'website': v.website,
        'description': v.description,
        'product_count': len(v.products),
    }


def serialize_vendor_detail(v):
    data = serialize_vendor(v)
    data['products'] = [
        {
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'lifecycle_stage': p.lifecycle_stage.value if p.lifecycle_stage else None,
            'versions': [
                {'id': pv.id, 'version': pv.version, 'release_date': pv.release_date.isoformat() if pv.release_date else None}
                for pv in p.versions
            ],
        }
        for p in v.products
    ]
    return data


def serialize_component(c):
    return {
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'short_description': c.short_description,
        'function_names': [f.name for f in c.functions],
    }


def serialize_function(f):
    return {
        'id': f.id,
        'name': f.name,
        'description': f.description,
        'criticality': f.criticality.value if f.criticality else None,
        'functional_area': f.functional_area.name if f.functional_area else None,
        'functional_area_id': f.functional_area_id,
    }


def serialize_functional_area(fa):
    return {
        'id': fa.id,
        'name': fa.name,
        'description': fa.description,
        'functions': [serialize_function(f) for f in fa.functions],
    }


def serialize_configuration(c):
    return {
        'id': c.id,
        'agency': c.agency.name if c.agency else None,
        'agency_id': c.agency_id,
        'function': c.function.name if c.function else None,
        'function_id': c.function_id,
        'component': c.component.name if c.component else None,
        'component_id': c.component_id,
        'status': c.status,
        'deployment_date': c.deployment_date.isoformat() if c.deployment_date else None,
        'implementation_notes': c.implementation_notes,
        'products': [
            {
                'product': cp.product.name if cp.product else None,
                'vendor': cp.product.vendor.name if cp.product and cp.product.vendor else None,
                'version': cp.product_version.version if cp.product_version else None,
            }
            for cp in c.products
        ],
        'service_types': [st.name for st in c.service_types],
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Agency endpoints
# ---------------------------------------------------------------------------

@api_v1.route('/agencies')
def list_agencies():
    q = Agency.query.order_by(Agency.name)
    search = request.args.get('search', '').strip()
    if search:
        q = q.filter(Agency.name.ilike(f'%{search}%'))
    items, meta = paginate(q)
    return api_ok({'items': [serialize_agency(a) for a in items], **meta})


@api_v1.route('/agencies/<int:agency_id>')
def get_agency(agency_id):
    a = Agency.query.options(
        joinedload(Agency.configurations)
        .joinedload(Configuration.function),
        joinedload(Agency.configurations)
        .joinedload(Configuration.component),
        joinedload(Agency.configurations)
        .joinedload(Configuration.products)
        .joinedload(ConfigurationProduct.product)
        .joinedload(Product.vendor),
        joinedload(Agency.configurations)
        .joinedload(Configuration.products)
        .joinedload(ConfigurationProduct.product_version),
        joinedload(Agency.configurations)
        .joinedload(Configuration.service_types),
    ).get(agency_id)
    if not a:
        return api_error('Agency not found', 404)
    return api_ok(serialize_agency_detail(a))


# ---------------------------------------------------------------------------
# Vendor endpoints
# ---------------------------------------------------------------------------

@api_v1.route('/vendors')
def list_vendors():
    q = Vendor.query.order_by(Vendor.name)
    search = request.args.get('search', '').strip()
    if search:
        q = q.filter(Vendor.name.ilike(f'%{search}%'))
    items, meta = paginate(q)
    return api_ok({'items': [serialize_vendor(v) for v in items], **meta})


@api_v1.route('/vendors/<int:vendor_id>')
def get_vendor(vendor_id):
    v = Vendor.query.options(
        joinedload(Vendor.products).joinedload(Product.versions),
    ).get(vendor_id)
    if not v:
        return api_error('Vendor not found', 404)
    return api_ok(serialize_vendor_detail(v))


# ---------------------------------------------------------------------------
# Component endpoints
# ---------------------------------------------------------------------------

@api_v1.route('/components')
def list_components():
    q = Component.query.order_by(Component.name)
    search = request.args.get('search', '').strip()
    if search:
        q = q.filter(Component.name.ilike(f'%{search}%'))
    items, meta = paginate(q)
    return api_ok({'items': [serialize_component(c) for c in items], **meta})


@api_v1.route('/components/<int:component_id>')
def get_component(component_id):
    c = Component.query.options(
        joinedload(Component.functions),
    ).get(component_id)
    if not c:
        return api_error('Component not found', 404)
    return api_ok(serialize_component(c))


# ---------------------------------------------------------------------------
# Function endpoints (returns full taxonomy grouped by functional area)
# ---------------------------------------------------------------------------

@api_v1.route('/functions')
def list_functions():
    q = FunctionalArea.query.options(
        joinedload(FunctionalArea.functions),
    ).order_by(FunctionalArea.name)
    items, meta = paginate(q)
    return api_ok({'items': [serialize_functional_area(fa) for fa in items], **meta})


@api_v1.route('/functions/<int:function_id>')
def get_function(function_id):
    f = Function.query.options(
        joinedload(Function.functional_area),
    ).get(function_id)
    if not f:
        return api_error('Function not found', 404)
    return api_ok(serialize_function(f))


# ---------------------------------------------------------------------------
# Configuration endpoints
# ---------------------------------------------------------------------------

@api_v1.route('/configurations')
def list_configurations():
    q = Configuration.query.options(
        joinedload(Configuration.agency),
        joinedload(Configuration.function),
        joinedload(Configuration.component),
        joinedload(Configuration.products).joinedload(ConfigurationProduct.product).joinedload(Product.vendor),
        joinedload(Configuration.products).joinedload(ConfigurationProduct.product_version),
        joinedload(Configuration.service_types),
    ).order_by(Configuration.updated_at.desc())

    # Filters
    agency_id = request.args.get('agency_id', type=int)
    component_id = request.args.get('component_id', type=int)
    function_id = request.args.get('function_id', type=int)
    status = request.args.get('status', '').strip()

    if agency_id:
        q = q.filter(Configuration.agency_id == agency_id)
    if component_id:
        q = q.filter(Configuration.component_id == component_id)
    if function_id:
        q = q.filter(Configuration.function_id == function_id)
    if status:
        q = q.filter(Configuration.status == status)

    items, meta = paginate(q)
    return api_ok({'items': [serialize_configuration(c) for c in items], **meta})


@api_v1.route('/configurations/<int:config_id>')
def get_configuration(config_id):
    c = Configuration.query.options(
        joinedload(Configuration.agency),
        joinedload(Configuration.function),
        joinedload(Configuration.component),
        joinedload(Configuration.products).joinedload(ConfigurationProduct.product).joinedload(Product.vendor),
        joinedload(Configuration.products).joinedload(ConfigurationProduct.product_version),
        joinedload(Configuration.service_types),
    ).get(config_id)
    if not c:
        return api_error('Configuration not found', 404)
    return api_ok(serialize_configuration(c))


# ---------------------------------------------------------------------------
# Search endpoint — unified full-text search across entities
# ---------------------------------------------------------------------------

SEARCHABLE_TYPES = ('agency', 'vendor', 'component', 'product', 'function', 'configuration')


@api_v1.route('/search')
def search():
    """Search across entities.

    Query params:
        q       — search term (required, min 2 chars)
        type    — restrict to entity type (optional, comma-separated)
        page    — page number (default 1)
        per_page — results per page (default 25, max 100)
    """
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return api_error('Search query must be at least 2 characters', 400)

    type_filter = request.args.get('type', '').strip().lower()
    types = [t.strip() for t in type_filter.split(',') if t.strip()] if type_filter else list(SEARCHABLE_TYPES)

    for t in types:
        if t not in SEARCHABLE_TYPES:
            return api_error(f"Invalid type '{t}'. Valid: {', '.join(SEARCHABLE_TYPES)}", 400)

    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int), MAX_PAGE_SIZE)
    pattern = f'%{q}%'

    results = []

    if 'agency' in types:
        for a in Agency.query.filter(
            or_(Agency.name.ilike(pattern), Agency.description.ilike(pattern), Agency.location.ilike(pattern))
        ).limit(per_page).all():
            results.append({'type': 'agency', 'id': a.id, 'name': a.name, 'description': a.description})

    if 'vendor' in types:
        for v in Vendor.query.filter(
            or_(Vendor.name.ilike(pattern), Vendor.description.ilike(pattern))
        ).limit(per_page).all():
            results.append({'type': 'vendor', 'id': v.id, 'name': v.name, 'description': v.description})

    if 'component' in types:
        for c in Component.query.filter(
            or_(Component.name.ilike(pattern), Component.description.ilike(pattern))
        ).limit(per_page).all():
            results.append({'type': 'component', 'id': c.id, 'name': c.name, 'description': c.description})

    if 'product' in types:
        for p in Product.query.options(joinedload(Product.vendor)).filter(
            or_(Product.name.ilike(pattern), Product.description.ilike(pattern))
        ).limit(per_page).all():
            results.append({
                'type': 'product', 'id': p.id, 'name': p.name,
                'description': p.description,
                'vendor': p.vendor.name if p.vendor else None,
            })

    if 'function' in types:
        for f in Function.query.options(joinedload(Function.functional_area)).filter(
            or_(Function.name.ilike(pattern), Function.description.ilike(pattern))
        ).limit(per_page).all():
            results.append({
                'type': 'function', 'id': f.id, 'name': f.name,
                'description': f.description,
                'functional_area': f.functional_area.name if f.functional_area else None,
            })

    if 'configuration' in types:
        for c in Configuration.query.options(
            joinedload(Configuration.agency),
            joinedload(Configuration.function),
            joinedload(Configuration.component),
        ).filter(
            Configuration.implementation_notes.ilike(pattern)
        ).limit(per_page).all():
            results.append({
                'type': 'configuration', 'id': c.id,
                'name': f"{c.agency.name} / {c.function.name} / {c.component.name}" if c.agency and c.function and c.component else f"Configuration #{c.id}",
                'description': c.implementation_notes,
            })

    # Simple pagination over the combined results
    total = len(results)
    start = (page - 1) * per_page
    paged = results[start:start + per_page]

    return api_ok({
        'items': paged,
        'query': q,
        'types': types,
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': max(1, (total + per_page - 1) // per_page),
    })
