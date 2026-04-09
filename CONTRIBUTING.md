# Contributing to See-Tran

Thank you for your interest in contributing to See-Tran! This guide covers everything you need to get started.

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Tailwind CSS build)
- Git

### Getting Started

```bash
# Clone the repo
git clone https://github.com/your-org/see-tran.git
cd see-tran

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt
npm install

# Set required environment variables
export SECRET_KEY=dev-secret

# Initialize and seed the database
flask db upgrade
flask seed all

# Build CSS (watch mode for development)
npm run build

# Run the app
flask run
```

App runs at http://localhost:5000.

### Optional Environment Variables

```
CLAUDE_API_KEY=sk-ant-...              # Required only for AI agent features
OAUTH_GOOGLE_CLIENT_ID=...            # Google login
OAUTH_GOOGLE_CLIENT_SECRET=...
OAUTH_MS_CLIENT_ID=...                # Microsoft login
OAUTH_MS_CLIENT_SECRET=...
SUPER_ADMIN_EMAIL=you@example.com     # Bypass auth for admin access in dev
```

---

## Running Tests

```bash
pytest tests/
```

Tests use an in-memory SQLite database. No external services required.

---

## Seeding Data

Seed data lives in JSON files under `data/` and is loaded via CLI:

```bash
flask seed all                  # Load everything in dependency order
flask seed agencies             # Load just agencies
flask seed vendors              # Load just vendors
flask seed components           # etc.
flask seed functional-areas
flask seed functions
flask seed configurations
flask seed integrations
flask seed standards
```

---

## Running AI Agents

Agents require a `CLAUDE_API_KEY` environment variable.

```bash
flask agent run agency --id 42          # Research a single agency
flask agent run agency --all --dry-run  # Preview changes for all agencies
flask agent status                      # Show agent run history
```

Agent results are logged to `logs/agent_audit.jsonl`.

---

## Project Structure

```
see-tran/
  app/
    __init__.py          # App factory
    auth.py              # OAuth (Google, Microsoft)
    models/tran.py       # All domain models
    routes/              # Flask blueprints
      main.py            # Pages: index, functional areas, components, vendors
      agency.py          # Agency pages
      configurations.py  # Configuration CRUD
      integrations.py    # Integration points
      admin.py           # Admin dashboard, agent UI, suggestion review
      api_v1.py          # Public read-only API (/api/v1/)
    templates/           # Jinja2 + HTMX templates
    static/              # CSS, JS, images
    agents/              # AI research agents
    utils/errors.py      # API response helpers
    mcp_server.py        # MCP tools for Claude Code
  config.py              # Flask config classes
  run.py                 # App entry + CLI commands
  data/                  # Seed JSON files
  tests/                 # Pytest tests
  migrations/            # Alembic migrations
```

---

## Code Conventions

### Route Patterns

- **Page routes** render full Jinja templates: `GET /agencies/42`
- **Fragment routes** return HTMX partials: `GET /api/configurations/42/row`
- **JSON API endpoints** live under `/api/` and use the standard envelope:

```json
{"ok": true, "data": {...}}
{"ok": false, "error": "message", "code": 400}
```

Use `api_ok()`, `api_error()`, `api_validation_error()` from `app/utils/errors.py`.

### Public API (v1)

Read-only, unauthenticated endpoints under `/api/v1/`:

```
GET /api/v1/agencies          # Paginated list (search, page, per_page)
GET /api/v1/agencies/<id>     # Detail with configurations
GET /api/v1/vendors
GET /api/v1/vendors/<id>      # Detail with products
GET /api/v1/components
GET /api/v1/components/<id>
GET /api/v1/functions          # Grouped by functional area
GET /api/v1/functions/<id>
GET /api/v1/configurations     # Filterable by agency_id, component_id, etc.
GET /api/v1/configurations/<id>
GET /api/v1/search?q=<term>&type=<entity>
```

### Templates

- Full pages: `templates/<entity>.html`
- Fragments: `templates/fragments/<entity>_<fragment>.html`
- Admin: `templates/admin/<page>.html`

### Models

All domain models are in `app/models/tran.py`. Key uniqueness constraints:

- `Agency.name`, `Vendor.name`, `Product.name` are unique
- `Configuration` is unique on `(agency_id, function_id, component_id)`
- `ProductVersion` is unique on `(product_id, version)`

---

## Data Quality Standards

When contributing seed data or making database changes:

1. **Agency names** should be the official full name (e.g., "Los Angeles County Metropolitan Transportation Authority", not "LA Metro")
2. **Vendor names** should match the company's current legal/brand name
3. **Components** should be generic technology categories, not product names
4. **Service types** are standardized: Fixed, Rail, Paratransit, OnDemand
5. **Descriptions** should be factual and concise (under 500 chars)

---

## PR Conventions

1. Create a feature branch from `main`
2. Keep PRs focused on a single feature or fix
3. Include a clear description of what changed and why
4. Ensure `pytest tests/` passes before submitting
5. If adding a new model or field, include an Alembic migration (`flask db migrate -m "description"`)

---

## MCP Server (for AI agents and Claude Code)

The MCP server exposes database CRUD as tools for Claude Code:

```bash
python -m app.mcp_server
```

Auto-discovered via `mcp.json` at the repo root. Tools include `list_agencies`, `upsert_vendor`, `create_suggestion`, etc.

---

## Questions?

Open an issue on GitHub or check the project's `CLAUDE.md` for detailed architecture documentation.
