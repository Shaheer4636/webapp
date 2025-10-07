

from __future__ import annotations
import os
from decimal import Decimal
from typing import Optional

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    flash,
)
from sqlalchemy import create_engine, Column, Integer, String, Text, Numeric, select
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from dotenv import load_dotenv

# Load local .env if present (for local dev). In Azure Web App, use App Settings.
load_dotenv()

# ----------------------
# Config & DB setup
# ----------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True))

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Item id={self.id} name={self.name!r}>"

# Create tables if they don't exist
Base.metadata.create_all(engine)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ----------------------
# Templates (inline)
# ----------------------
layout_tpl = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title or 'Items App' }}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
  <style>
    :root { --bg: #0f172a; --card:#111827; --muted:#94a3b8; --fg:#e5e7eb; --accent:#22d3ee; --red:#ef4444; }
    *{ box-sizing:border-box; }
    body{ margin:0; font-family:Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:linear-gradient(120deg,#0b1220,#0f172a); color:var(--fg); }
    .container{ max-width: 980px; margin: 40px auto; padding: 0 16px; }
    header{ display:flex; align-items:center; justify-content:space-between; margin-bottom: 18px; }
    .title{ font-weight:700; letter-spacing:0.3px; }
    .card{ background: rgba(17,24,39,0.75); backdrop-filter: blur(6px); border:1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.35); }
    .actions{ display:flex; gap:8px; flex-wrap: wrap; }
    a.button, button.button{ appearance:none; border:none; background:#0ea5e9; color:white; padding:8px 12px; border-radius: 10px; text-decoration:none; font-weight:600; cursor:pointer; }
    a.button.secondary, button.secondary{ background:#334155; color:#e5e7eb; }
    a.button.danger, button.danger{ background: var(--red); }
    table{ width:100%; border-collapse: collapse; margin-top: 10px; }
    th, td{ text-align:left; padding: 10px 8px; border-bottom:1px solid rgba(255,255,255,0.06); }
    th{ font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
    tbody tr:hover{ background: rgba(255,255,255,0.03); }
    .muted{ color: var(--muted); }
    form.inline{ display:inline; }
    .input{ width:100%; padding:10px 12px; background:#0b1220; color:var(--fg); border:1px solid rgba(255,255,255,0.12); border-radius:10px; }
    .grid{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .grid-1{ grid-template-columns: 1fr; }
    .field label{ display:block; margin-bottom:6px; color: var(--muted); font-size: 14px; }
    .flash{ background: rgba(34,211,238,0.12); border:1px solid rgba(34,211,238,0.35); padding:10px 12px; border-radius:10px; margin-bottom:12px; }
    footer{ margin-top: 24px; color: var(--muted); font-size: 13px; text-align:center; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1 class="title">📦 {{ title or 'Items' }}</h1>
      <div class="actions">
        <a href="{{ url_for('new_item') }}" class="button">➕ New Item</a>
        <a href="{{ url_for('index') }}" class="button secondary">⟳ Refresh</a>
      </div>
    </header>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for msg in messages %}
          <div class="flash">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="card">
      {% block content %}{% endblock %}
    </div>

    <footer>
      Connected to: <span class="muted">{{ db_url_display }}</span>
    </footer>
  </div>
</body>
</html>
"""

index_tpl = """
{% extends 'layout' %}
{% block content %}
  {% if items %}
    <table>
      <thead>
        <tr>
          <th style="width:70px">ID</th>
          <th>Name</th>
          <th>Description</th>
          <th style="width:120px">Price</th>
          <th style="width:200px">Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for i in items %}
          <tr>
            <td>{{ i.id }}</td>
            <td>{{ i.name }}</td>
            <td class="muted">{{ i.description or '' }}</td>
            <td>{{ '%.2f'|format(i.price) if i.price is not none else '' }}</td>
            <td>
              <a class="button secondary" href="{{ url_for('edit_item', item_id=i.id) }}">✏️ Edit</a>
              <form class="inline" method="post" action="{{ url_for('delete_item', item_id=i.id) }}" onsubmit="return confirm('Delete this item?');">
                <button class="button danger" type="submit">🗑️ Delete</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p class="muted">No items yet. Create your first one.</p>
  {% endif %}
{% endblock %}
"""

form_tpl = """
{% extends 'layout' %}
{% block content %}
  <form method="post">
    <div class="grid grid-1">
      <div class="field">
        <label for="name">Name *</label>
        <input class="input" id="name" name="name" value="{{ item.name if item else '' }}" required>
      </div>
      <div class="field">
        <label for="description">Description</label>
        <textarea class="input" id="description" name="description" rows="3">{{ item.description if item else '' }}</textarea>
      </div>
      <div class="field">
        <label for="price">Price</label>
        <input class="input" id="price" name="price" type="number" step="0.01" min="0" value="{{ item.price if item and item.price is not none else '' }}">
      </div>
    </div>
    <div style="margin-top:12px; display:flex; gap:8px;">
      <button class="button" type="submit">💾 Save</button>
      <a class="button secondary" href="{{ url_for('index') }}">Cancel</a>
    </div>
  </form>
{% endblock %}
"""

# Register template strings
# We use Flask's template loader by overriding jinja loader with a dict-like loader.
from jinja2 import DictLoader
app.jinja_loader = DictLoader({
    'layout': layout_tpl,
    'index.html': index_tpl,
    'form.html': form_tpl,
})

# Helper to mask credentials in the displayed DB URL
from urllib.parse import urlparse

def _display_dsn(dsn: str) -> str:
    try:
        p = urlparse(dsn)
        if p.username or p.password:
            netloc = p.hostname or ''
            if p.port:
                netloc += f":{p.port}"
            return f"{p.scheme}://***:***@{netloc}{p.path}"
        return dsn
    except Exception:
        return dsn

@app.context_processor
def inject_globals():
    return {"db_url_display": _display_dsn(DATABASE_URL)}

# ----------------------
# Routes
# ----------------------
@app.get("/")
def index():
    session = SessionLocal()
    try:
        items = session.execute(select(Item).order_by(Item.id.desc())).scalars().all()
        return render_template_string(index_tpl, title="Items", items=items)
    finally:
        session.close()

@app.get("/item/new")
def new_item():
    return render_template_string(form_tpl, title="New Item", item=None)

@app.post("/item/new")
def create_item():
    name = request.form.get("name", "").strip()
    description = request.form.get("description") or None
    price_raw: Optional[str] = request.form.get("price")
    price: Optional[Decimal] = None
    if not name:
        flash("Name is required")
        return redirect(url_for("new_item"))
    if price_raw:
        try:
            price = Decimal(price_raw)
        except Exception:  # invalid decimal
            flash("Price must be a number")
            return redirect(url_for("new_item"))

    session = SessionLocal()
    try:
        item = Item(name=name, description=description, price=price)
        session.add(item)
        session.commit()
        flash("Item created")
    except Exception as e:
        session.rollback()
        flash(f"Error creating item: {e}")
    finally:
        session.close()
    return redirect(url_for("index"))

@app.get("/item/<int:item_id>/edit")
def edit_item(item_id: int):
    session = SessionLocal()
    try:
        item = session.get(Item, item_id)
        if not item:
            flash("Item not found")
            return redirect(url_for("index"))
        return render_template_string(form_tpl, title="Edit Item", item=item)
    finally:
        session.close()

@app.post("/item/<int:item_id>/edit")
def update_item(item_id: int):
    name = request.form.get("name", "").strip()
    description = request.form.get("description") or None
    price_raw: Optional[str] = request.form.get("price")
    price: Optional[Decimal] = None
    if not name:
        flash("Name is required")
        return redirect(url_for("edit_item", item_id=item_id))
    if price_raw:
        try:
            price = Decimal(price_raw)
        except Exception:
            flash("Price must be a number")
            return redirect(url_for("edit_item", item_id=item_id))

    session = SessionLocal()
    try:
        item = session.get(Item, item_id)
        if not item:
            flash("Item not found")
            return redirect(url_for("index"))
        item.name = name
        item.description = description
        item.price = price
        session.commit()
        flash("Item updated")
    except Exception as e:
        session.rollback()
        flash(f"Error updating item: {e}")
    finally:
        session.close()
    return redirect(url_for("index"))

@app.post("/item/<int:item_id>/delete")
def delete_item(item_id: int):
    session = SessionLocal()
    try:
        item = session.get(Item, item_id)
        if not item:
            flash("Item not found")
            return redirect(url_for("index"))
        session.delete(item)
        session.commit()
        flash("Item deleted")
    except Exception as e:
        session.rollback()
        flash(f"Error deleting item: {e}")
    finally:
        session.close()
    return redirect(url_for("index"))

@app.get("/healthz")
def healthz():
    # Lightweight DB check
    session = SessionLocal()
    try:
        session.execute(select(1))
        return {"status": "ok"}, 200
    except Exception as e:
        return {"status": "error", "detail": str(e)}, 500
    finally:
        session.close()

@app.teardown_appcontext
def remove_session(exception=None):  # pragma: no cover
    SessionLocal.remove()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    print(f"\n>>> Running on http://{host}:{port} (DB: {DATABASE_URL})\n")
    app.run(host=host, port=port, debug=debug)
