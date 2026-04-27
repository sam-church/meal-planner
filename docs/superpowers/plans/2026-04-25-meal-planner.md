# Meal Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Flask web app for weekly meal planning, recipe management, shopping list generation, and Google Calendar sync.

**Architecture:** Flask REST API with SQLAlchemy/SQLite backend; all data operations through `/api/` JSON endpoints; single-page vanilla JS frontend served at `/`.

**Tech Stack:** Python 3.10+, Flask 3.x, Flask-SQLAlchemy, SQLite, requests, beautifulsoup4, google-api-python-client, google-auth-oauthlib, pytz, pytest, pytest-flask

---

### Task 1: Project Foundation

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `run.py`
- Create/Modify: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/database.py`
- Create: `app/models/__init__.py`
- Create: `app/api/__init__.py`
- Create: `app/services/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_app.py`

- [ ] Write failing test `tests/test_app.py`
- [ ] Run `pytest tests/test_app.py -v` — expect FAIL (app doesn't exist yet)
- [ ] Create `requirements.txt`:

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
SQLAlchemy==2.0.36
requests==2.32.3
beautifulsoup4==4.12.3
google-api-python-client==2.154.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
pytz==2024.1
pytest==8.3.4
pytest-flask==1.3.0
```

- [ ] Create `config.py`:

```python
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'meal_planner.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

LUNCH_START = "11:30"
DINNER_START = "18:00"
SUNDAY_PREP_START = "14:00"
CALENDAR_NAME = "Tripe F"
CALENDAR_TIMEZONE = "America/New_York"
SPOONACULAR_API_KEY = os.environ.get("SPOONACULAR_API_KEY", "")

SLOT_KEYS = [
    'mon_lunch', 'mon_dinner',
    'tue_lunch', 'tue_dinner',
    'wed_lunch', 'wed_dinner',
    'thu_lunch', 'thu_dinner',
    'fri_lunch', 'fri_dinner',
    'sunday_prep',
]
```

- [ ] Create `run.py`:

```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

- [ ] Append to `.gitignore`:

```
data/token.json
data/*.db
data/credentials.json
__pycache__/
*.pyc
.env
venv/
.venv/
```

- [ ] Create `app/__init__.py` (app factory):

```python
from flask import Flask
from .database import db

def create_app(config=None):
    app = Flask(__name__, static_folder='static', static_url_path='')
    app.config.from_object('config')
    if config:
        app.config.update(config)

    db.init_app(app)

    with app.app_context():
        from . import models  # noqa: ensure models are registered
        db.create_all()

    from .api import pantry, preferences, recipes, weeks
    app.register_blueprint(pantry.bp)
    app.register_blueprint(preferences.bp)
    app.register_blueprint(recipes.bp)
    app.register_blueprint(weeks.bp)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    return app
```

- [ ] Create `app/database.py`:

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```

- [ ] Create `app/models/__init__.py` — empty file (ensures models imported)
- [ ] Create `app/api/__init__.py` — empty
- [ ] Create `app/services/__init__.py` — empty

- [ ] Create `tests/conftest.py`:

```python
import pytest
from app import create_app
from app.database import db as _db

@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()
```

- [ ] Write `tests/test_app.py`:

```python
def test_app_creates(app):
    assert app is not None

def test_db_tables_exist(app):
    with app.app_context():
        from app.database import db
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        assert 'recipes' in tables
        assert 'week_plans' in tables
        assert 'shopping_lists' in tables
        assert 'pantry_staples' in tables
        assert 'preferences' in tables
```

- [ ] Run `pytest tests/test_app.py -v` — expect PASS (output contains `2 passed`)
- [ ] `git commit -m "feat: project foundation — app factory, config, db setup"`

---

### Task 2: Data Models

**Files:**
- Create: `app/models/recipe.py`
- Create: `app/models/week_plan.py`
- Create: `app/models/shopping_list.py`
- Create: `app/models/pantry_staple.py`
- Create: `app/models/preference.py`
- Modify: `app/models/__init__.py`
- Test: `tests/test_models.py`

- [ ] Write failing test `tests/test_models.py`
- [ ] Run `pytest tests/test_models.py -v` — expect FAIL (models don't exist yet)
- [ ] Create `app/models/recipe.py`:

```python
from app.database import db

class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    source_url = db.Column(db.Text)
    source_api_id = db.Column(db.Text)
    base_servings = db.Column(db.Integer, nullable=False, default=2)
    ingredients = db.Column(db.JSON, default=list)
    cook_method = db.Column(db.JSON, default=list)
    prep_time_mins = db.Column(db.Integer)
    cook_time_mins = db.Column(db.Integer)
    makes_leftovers = db.Column(db.Boolean, default=False)
    nutrition = db.Column(db.JSON)
    tags = db.Column(db.JSON, default=list)
    notes = db.Column(db.Text)
    last_used_date = db.Column(db.Date)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'source_url': self.source_url,
            'source_api_id': self.source_api_id,
            'base_servings': self.base_servings,
            'ingredients': self.ingredients or [],
            'cook_method': self.cook_method or [],
            'prep_time_mins': self.prep_time_mins,
            'cook_time_mins': self.cook_time_mins,
            'makes_leftovers': self.makes_leftovers,
            'nutrition': self.nutrition,
            'tags': self.tags or [],
            'notes': self.notes,
            'last_used_date': self.last_used_date.isoformat() if self.last_used_date else None,
        }
```

- [ ] Create `app/models/week_plan.py`:

```python
from app.database import db

class WeekPlan(db.Model):
    __tablename__ = 'week_plans'
    id = db.Column(db.Integer, primary_key=True)
    week_start_date = db.Column(db.Date, nullable=False)
    slots = db.Column(db.JSON, default=dict)
    calendar_synced = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'week_start_date': self.week_start_date.isoformat() if self.week_start_date else None,
            'slots': self.slots or {},
            'calendar_synced': self.calendar_synced,
            'notes': self.notes,
        }
```

- [ ] Create `app/models/shopping_list.py`:

```python
from app.database import db

class ShoppingList(db.Model):
    __tablename__ = 'shopping_lists'
    id = db.Column(db.Integer, primary_key=True)
    week_plan_id = db.Column(db.Integer, db.ForeignKey('week_plans.id'), nullable=False)
    items = db.Column(db.JSON, default=dict)
    generated_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'week_plan_id': self.week_plan_id,
            'items': self.items or {},
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
        }
```

- [ ] Create `app/models/pantry_staple.py`:

```python
from app.database import db

class PantryStaple(db.Model):
    __tablename__ = 'pantry_staples'
    id = db.Column(db.Integer, primary_key=True)
    ingredient_name = db.Column(db.Text, nullable=False, unique=True)
    category = db.Column(db.Text, default='other')

    def to_dict(self):
        return {'id': self.id, 'ingredient_name': self.ingredient_name, 'category': self.category}
```

- [ ] Create `app/models/preference.py`:

```python
from app.database import db

class Preference(db.Model):
    __tablename__ = 'preferences'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text, nullable=False)
    value = db.Column(db.Text, nullable=False)
    scope = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'type': self.type, 'value': self.value, 'scope': self.scope}
```

- [ ] Update `app/models/__init__.py`:

```python
from .recipe import Recipe
from .week_plan import WeekPlan
from .shopping_list import ShoppingList
from .pantry_staple import PantryStaple
from .preference import Preference
```

- [ ] Write `tests/test_models.py`:

```python
from datetime import date
from app.models.recipe import Recipe
from app.models.week_plan import WeekPlan
from app.models.pantry_staple import PantryStaple
from app.models.preference import Preference

def test_recipe_create(db):
    r = Recipe(name='Pasta', base_servings=2, ingredients=[{'name': 'pasta', 'quantity': 200, 'unit': 'g', 'category': 'pantry'}], cook_method=['stove'])
    db.session.add(r)
    db.session.commit()
    assert r.id is not None
    assert r.makes_leftovers is False

def test_recipe_to_dict(db):
    r = Recipe(name='Pasta', base_servings=2)
    db.session.add(r)
    db.session.commit()
    d = r.to_dict()
    assert d['name'] == 'Pasta'
    assert d['base_servings'] == 2
    assert d['last_used_date'] is None

def test_week_plan_create(db):
    wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={})
    db.session.add(wp)
    db.session.commit()
    assert wp.id is not None
    assert wp.calendar_synced is False

def test_pantry_staple_create(db):
    s = PantryStaple(ingredient_name='olive oil', category='pantry')
    db.session.add(s)
    db.session.commit()
    assert s.id is not None

def test_preference_create(db):
    p = Preference(type='like', value='spicy', scope='ingredient')
    db.session.add(p)
    db.session.commit()
    assert p.id is not None
```

- [ ] Run `pytest tests/test_models.py -v` — expect PASS (output contains `5 passed`)
- [ ] `git commit -m "feat: add SQLAlchemy models for all 5 tables"`

---

### Task 3: Pantry Staples API

**Files:**
- Create: `app/api/pantry.py`
- Test: `tests/test_pantry_api.py`

- [ ] Write failing test `tests/test_pantry_api.py`
- [ ] Run `pytest tests/test_pantry_api.py -v` — expect FAIL (blueprint doesn't exist yet)
- [ ] Create `app/api/pantry.py`:

```python
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.pantry_staple import PantryStaple

bp = Blueprint('pantry', __name__, url_prefix='/api/pantry')

@bp.route('', methods=['GET'])
def list_staples():
    staples = PantryStaple.query.all()
    return jsonify([s.to_dict() for s in staples])

@bp.route('', methods=['POST'])
def add_staple():
    data = request.get_json()
    staple = PantryStaple(
        ingredient_name=data['ingredient_name'],
        category=data.get('category', 'other'),
    )
    db.session.add(staple)
    db.session.commit()
    return jsonify(staple.to_dict()), 201

@bp.route('/<int:staple_id>', methods=['DELETE'])
def delete_staple(staple_id):
    staple = PantryStaple.query.get_or_404(staple_id)
    db.session.delete(staple)
    db.session.commit()
    return '', 204
```

- [ ] Write `tests/test_pantry_api.py`:

```python
import json

def test_list_pantry_empty(client):
    resp = client.get('/api/pantry')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_add_pantry_staple(client):
    resp = client.post('/api/pantry', json={'ingredient_name': 'olive oil', 'category': 'pantry'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['ingredient_name'] == 'olive oil'
    assert data['category'] == 'pantry'
    assert 'id' in data

def test_list_pantry_after_add(client):
    client.post('/api/pantry', json={'ingredient_name': 'salt', 'category': 'pantry'})
    resp = client.get('/api/pantry')
    assert resp.status_code == 200
    items = resp.get_json()
    assert len(items) == 1
    assert items[0]['ingredient_name'] == 'salt'

def test_delete_pantry_staple(client):
    add_resp = client.post('/api/pantry', json={'ingredient_name': 'pepper'})
    staple_id = add_resp.get_json()['id']
    del_resp = client.delete(f'/api/pantry/{staple_id}')
    assert del_resp.status_code == 204
    list_resp = client.get('/api/pantry')
    assert list_resp.get_json() == []

def test_delete_nonexistent_pantry_staple(client):
    resp = client.delete('/api/pantry/999')
    assert resp.status_code == 404
```

- [ ] Run `pytest tests/test_pantry_api.py -v` — expect PASS (output contains `5 passed`)
- [ ] `git commit -m "feat: pantry staples CRUD API"`

---

### Task 4: Preferences API

**Files:**
- Create: `app/api/preferences.py`
- Test: `tests/test_preferences_api.py`

- [ ] Write failing test `tests/test_preferences_api.py`
- [ ] Run `pytest tests/test_preferences_api.py -v` — expect FAIL (blueprint doesn't exist yet)
- [ ] Create `app/api/preferences.py`:

```python
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.preference import Preference

bp = Blueprint('preferences', __name__, url_prefix='/api/preferences')

@bp.route('', methods=['GET'])
def list_preferences():
    prefs = Preference.query.all()
    return jsonify([p.to_dict() for p in prefs])

@bp.route('', methods=['POST'])
def add_preference():
    data = request.get_json()
    pref = Preference(
        type=data['type'],
        value=data['value'],
        scope=data['scope'],
    )
    db.session.add(pref)
    db.session.commit()
    return jsonify(pref.to_dict()), 201

@bp.route('/<int:pref_id>', methods=['DELETE'])
def delete_preference(pref_id):
    pref = Preference.query.get_or_404(pref_id)
    db.session.delete(pref)
    db.session.commit()
    return '', 204
```

- [ ] Write `tests/test_preferences_api.py`:

```python
def test_list_preferences_empty(client):
    resp = client.get('/api/preferences')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_add_preference(client):
    resp = client.post('/api/preferences', json={'type': 'like', 'value': 'spicy', 'scope': 'ingredient'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['type'] == 'like'
    assert data['value'] == 'spicy'
    assert data['scope'] == 'ingredient'

def test_add_dislike(client):
    resp = client.post('/api/preferences', json={'type': 'dislike', 'value': 'fish', 'scope': 'ingredient'})
    assert resp.status_code == 201
    assert resp.get_json()['type'] == 'dislike'

def test_delete_preference(client):
    add_resp = client.post('/api/preferences', json={'type': 'like', 'value': 'Mediterranean', 'scope': 'cuisine'})
    pref_id = add_resp.get_json()['id']
    del_resp = client.delete(f'/api/preferences/{pref_id}')
    assert del_resp.status_code == 204
    list_resp = client.get('/api/preferences')
    assert list_resp.get_json() == []
```

- [ ] Run `pytest tests/test_preferences_api.py -v` — expect PASS (output contains `4 passed`)
- [ ] `git commit -m "feat: preferences CRUD API"`

---

### Task 5: Recipe CRUD API

**Files:**
- Create: `app/api/recipes.py`
- Test: `tests/test_recipes_api.py`

- [ ] Write failing test `tests/test_recipes_api.py` (CRUD tests only)
- [ ] Run `pytest tests/test_recipes_api.py -v` — expect FAIL (blueprint doesn't exist yet)
- [ ] Create `app/api/recipes.py`:

```python
from flask import Blueprint, request, jsonify, current_app
from app.database import db
from app.models.recipe import Recipe

bp = Blueprint('recipes', __name__, url_prefix='/api/recipes')

UPDATABLE_FIELDS = [
    'name', 'source_url', 'source_api_id', 'base_servings', 'ingredients',
    'cook_method', 'prep_time_mins', 'cook_time_mins', 'makes_leftovers',
    'nutrition', 'tags', 'notes',
]

@bp.route('', methods=['GET'])
def list_recipes():
    recipes = Recipe.query.order_by(Recipe.name).all()
    return jsonify([r.to_dict() for r in recipes])

@bp.route('', methods=['POST'])
def create_recipe():
    data = request.get_json()
    recipe = Recipe(
        name=data['name'],
        source_url=data.get('source_url'),
        source_api_id=data.get('source_api_id'),
        base_servings=data.get('base_servings', 2),
        ingredients=data.get('ingredients', []),
        cook_method=data.get('cook_method', []),
        prep_time_mins=data.get('prep_time_mins'),
        cook_time_mins=data.get('cook_time_mins'),
        makes_leftovers=data.get('makes_leftovers', False),
        nutrition=data.get('nutrition'),
        tags=data.get('tags', []),
        notes=data.get('notes'),
    )
    db.session.add(recipe)
    db.session.commit()
    return jsonify(recipe.to_dict()), 201

@bp.route('/<int:recipe_id>', methods=['GET'])
def get_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    return jsonify(recipe.to_dict())

@bp.route('/<int:recipe_id>', methods=['PUT'])
def update_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    data = request.get_json()
    for field in UPDATABLE_FIELDS:
        if field in data:
            setattr(recipe, field, data[field])
    db.session.commit()
    return jsonify(recipe.to_dict())

@bp.route('/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    return '', 204
```

- [ ] Write `tests/test_recipes_api.py` (CRUD tests only — search/import tests added in Task 6):

```python
SAMPLE_RECIPE = {
    'name': 'Chicken Stir Fry',
    'base_servings': 2,
    'ingredients': [{'name': 'chicken', 'quantity': 300, 'unit': 'g', 'category': 'protein'}],
    'cook_method': ['stove'],
    'prep_time_mins': 15,
    'cook_time_mins': 20,
    'makes_leftovers': False,
    'tags': ['quick'],
}

def test_list_recipes_empty(client):
    resp = client.get('/api/recipes')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_create_recipe(client):
    resp = client.post('/api/recipes', json=SAMPLE_RECIPE)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Chicken Stir Fry'
    assert data['base_servings'] == 2
    assert 'id' in data

def test_get_recipe(client):
    create_resp = client.post('/api/recipes', json=SAMPLE_RECIPE)
    recipe_id = create_resp.get_json()['id']
    resp = client.get(f'/api/recipes/{recipe_id}')
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Chicken Stir Fry'

def test_get_recipe_not_found(client):
    resp = client.get('/api/recipes/999')
    assert resp.status_code == 404

def test_update_recipe(client):
    create_resp = client.post('/api/recipes', json=SAMPLE_RECIPE)
    recipe_id = create_resp.get_json()['id']
    resp = client.put(f'/api/recipes/{recipe_id}', json={'name': 'Beef Stir Fry', 'makes_leftovers': True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Beef Stir Fry'
    assert data['makes_leftovers'] is True

def test_delete_recipe(client):
    create_resp = client.post('/api/recipes', json=SAMPLE_RECIPE)
    recipe_id = create_resp.get_json()['id']
    del_resp = client.delete(f'/api/recipes/{recipe_id}')
    assert del_resp.status_code == 204
    assert client.get(f'/api/recipes/{recipe_id}').status_code == 404
```

- [ ] Run `pytest tests/test_recipes_api.py -v` — expect PASS (output contains `6 passed`)
- [ ] `git commit -m "feat: recipe CRUD API"`

---

### Task 6: Spoonacular Search & Import

**Files:**
- Modify: `app/api/recipes.py`
- Create: `app/services/import_service.py`
- Test: `tests/test_import_service.py`

- [ ] Write failing test `tests/test_import_service.py`
- [ ] Run `pytest tests/test_import_service.py -v` — expect FAIL (import_service doesn't exist yet)
- [ ] Append to `app/api/recipes.py` (after existing routes):

```python
import requests as http_requests

@bp.route('/search', methods=['GET'])
def search_spoonacular():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'query parameter q is required'}), 400
    api_key = current_app.config.get('SPOONACULAR_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'Spoonacular API key not configured'}), 503
    try:
        resp = http_requests.get(
            'https://api.spoonacular.com/recipes/complexSearch',
            params={'query': query, 'apiKey': api_key, 'number': 10},
            timeout=10,
        )
        resp.raise_for_status()
        return jsonify(resp.json())
    except http_requests.RequestException as e:
        return jsonify({'error': f'Spoonacular search failed: {str(e)}'}), 502

@bp.route('/import/<int:spoonacular_id>', methods=['POST'])
def import_spoonacular(spoonacular_id):
    api_key = current_app.config.get('SPOONACULAR_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'Spoonacular API key not configured'}), 503
    try:
        resp = http_requests.get(
            f'https://api.spoonacular.com/recipes/{spoonacular_id}/information',
            params={'apiKey': api_key, 'includeNutrition': True},
            timeout=10,
        )
        resp.raise_for_status()
    except http_requests.RequestException as e:
        return jsonify({'error': f'Spoonacular fetch failed: {str(e)}'}), 502

    from app.services.import_service import map_spoonacular
    recipe_data = map_spoonacular(resp.json())
    recipe = Recipe(**recipe_data)
    db.session.add(recipe)
    db.session.commit()
    return jsonify(recipe.to_dict()), 201

@bp.route('/import-url', methods=['POST'])
def import_url():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'url is required'}), 400
    api_key = current_app.config.get('SPOONACULAR_API_KEY', '')
    from app.services.import_service import import_from_url
    recipe_data = import_from_url(url, api_key or None)
    if not recipe_data:
        return jsonify({'error': 'Could not parse recipe from URL — check the URL or fill in details manually'}), 422
    return jsonify(recipe_data)
```

- [ ] Create `app/services/import_service.py`:

```python
import json
import re
import requests
from bs4 import BeautifulSoup

SPOONACULAR_BASE = 'https://api.spoonacular.com'


def import_from_url(url, api_key=None):
    """Try Spoonacular extract endpoint first, then JSON-LD fallback."""
    if api_key:
        result = _try_spoonacular_extract(url, api_key)
        if result:
            return result
    return _try_json_ld(url)


def _try_spoonacular_extract(url, api_key):
    try:
        resp = requests.get(
            f'{SPOONACULAR_BASE}/recipes/extract',
            params={'url': url, 'apiKey': api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        return map_spoonacular(resp.json())
    except Exception:
        return None


def _try_json_ld(url):
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                recipes = _find_recipe_schema(data)
                if recipes:
                    return map_json_ld(recipes[0])
            except json.JSONDecodeError:
                continue
        return None
    except Exception:
        return None


def _find_recipe_schema(data):
    if isinstance(data, list):
        results = []
        for item in data:
            results.extend(_find_recipe_schema(item))
        return results
    if isinstance(data, dict):
        graph = data.get('@graph', [])
        if graph:
            return _find_recipe_schema(graph)
        if data.get('@type') == 'Recipe':
            return [data]
    return []


def map_spoonacular(data):
    ingredients = []
    for ext in data.get('extendedIngredients', []):
        ingredients.append({
            'name': ext.get('name', ''),
            'quantity': ext.get('amount', 0),
            'unit': ext.get('unit', ''),
            'category': '',
        })
    nutrition = None
    nutrients = data.get('nutrition', {}).get('nutrients', [])
    if nutrients:
        def find_n(name):
            for item in nutrients:
                if item.get('name') == name:
                    return item.get('amount')
            return None
        nutrition = {
            'calories': find_n('Calories'),
            'protein_g': find_n('Protein'),
            'carbs_g': find_n('Carbohydrates'),
            'fat_g': find_n('Fat'),
        }
    prep = data.get('preparationMinutes') or 0
    total = data.get('readyInMinutes') or 0
    cook = data.get('cookingMinutes') or max(0, total - prep)
    return {
        'name': data.get('title', ''),
        'source_url': data.get('sourceUrl', ''),
        'source_api_id': str(data.get('id', '')),
        'base_servings': data.get('servings', 2),
        'ingredients': ingredients,
        'cook_method': [],
        'prep_time_mins': prep,
        'cook_time_mins': cook,
        'makes_leftovers': False,
        'nutrition': nutrition,
        'tags': [],
        'notes': '',
    }


def map_json_ld(data):
    ingredients_raw = data.get('recipeIngredient', [])
    ingredients = [{'name': ing, 'quantity': '', 'unit': '', 'category': ''} for ing in ingredients_raw]

    def parse_duration(iso):
        if not iso:
            return 0
        h = re.search(r'(\d+)H', iso)
        m = re.search(r'(\d+)M', iso)
        hours = int(h.group(1)) if h else 0
        minutes = int(m.group(1)) if m else 0
        return hours * 60 + minutes

    servings = data.get('recipeYield', '2')
    if isinstance(servings, list):
        servings = servings[0] if servings else '2'
    try:
        servings = int(str(servings).split()[0])
    except (ValueError, IndexError):
        servings = 2

    return {
        'name': data.get('name', ''),
        'source_url': data.get('url', data.get('@id', '')),
        'source_api_id': None,
        'base_servings': servings,
        'ingredients': ingredients,
        'cook_method': [],
        'prep_time_mins': parse_duration(data.get('prepTime')),
        'cook_time_mins': parse_duration(data.get('cookTime')),
        'makes_leftovers': False,
        'nutrition': None,
        'tags': [],
        'notes': '',
    }
```

- [ ] Write `tests/test_import_service.py`:

```python
from unittest.mock import patch, MagicMock
from app.services.import_service import map_spoonacular, map_json_ld, import_from_url, _find_recipe_schema


def test_map_spoonacular_basic():
    data = {
        'title': 'Spaghetti Bolognese',
        'id': 123,
        'servings': 4,
        'preparationMinutes': 10,
        'cookingMinutes': 30,
        'sourceUrl': 'https://example.com/recipe',
        'extendedIngredients': [
            {'name': 'ground beef', 'amount': 0.5, 'unit': 'lb'},
        ],
        'nutrition': {'nutrients': [
            {'name': 'Calories', 'amount': 450},
            {'name': 'Protein', 'amount': 30},
        ]},
    }
    result = map_spoonacular(data)
    assert result['name'] == 'Spaghetti Bolognese'
    assert result['base_servings'] == 4
    assert result['prep_time_mins'] == 10
    assert result['cook_time_mins'] == 30
    assert len(result['ingredients']) == 1
    assert result['ingredients'][0]['name'] == 'ground beef'
    assert result['nutrition']['calories'] == 450
    assert result['cook_method'] == []


def test_map_json_ld_basic():
    data = {
        '@type': 'Recipe',
        'name': 'Avocado Toast',
        'url': 'https://skinnytaste.com/avocado-toast',
        'recipeYield': '2 servings',
        'prepTime': 'PT5M',
        'cookTime': 'PT10M',
        'recipeIngredient': ['2 slices bread', '1 avocado'],
    }
    result = map_json_ld(data)
    assert result['name'] == 'Avocado Toast'
    assert result['base_servings'] == 2
    assert result['prep_time_mins'] == 5
    assert result['cook_time_mins'] == 10
    assert len(result['ingredients']) == 2
    assert result['ingredients'][0]['name'] == '2 slices bread'
    assert result['nutrition'] is None


def test_find_recipe_schema_graph():
    data = {
        '@graph': [
            {'@type': 'WebPage', 'name': 'Page'},
            {'@type': 'Recipe', 'name': 'My Recipe'},
        ]
    }
    results = _find_recipe_schema(data)
    assert len(results) == 1
    assert results[0]['name'] == 'My Recipe'


def test_import_from_url_uses_json_ld_when_no_api_key():
    mock_html = '''<html><head>
    <script type="application/ld+json">
    {"@type": "Recipe", "name": "Test Recipe", "recipeYield": "2", "recipeIngredient": ["1 egg"]}
    </script></head></html>'''
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html
    with patch('app.services.import_service.requests.get', return_value=mock_resp):
        result = import_from_url('https://example.com/recipe', api_key=None)
    assert result is not None
    assert result['name'] == 'Test Recipe'


def test_import_from_url_returns_none_on_failure():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch('app.services.import_service.requests.get', return_value=mock_resp):
        result = import_from_url('https://example.com/404', api_key=None)
    assert result is None
```

- [ ] Run `pytest tests/test_import_service.py -v` — expect PASS (output contains `5 passed`)
- [ ] `git commit -m "feat: Spoonacular search/import and URL import with JSON-LD fallback"`

---

### Task 7: Week Plan CRUD API

**Files:**
- Create: `app/api/weeks.py`
- Test: `tests/test_weeks_api.py`

- [ ] Write failing test `tests/test_weeks_api.py`
- [ ] Run `pytest tests/test_weeks_api.py -v` — expect FAIL (blueprint doesn't exist yet)
- [ ] Create `app/api/weeks.py`:

```python
from datetime import date
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.week_plan import WeekPlan
from app.models.shopping_list import ShoppingList
from app.models.recipe import Recipe

bp = Blueprint('weeks', __name__, url_prefix='/api/weeks')

@bp.route('', methods=['GET'])
def list_weeks():
    weeks = WeekPlan.query.order_by(WeekPlan.week_start_date.desc()).all()
    return jsonify([w.to_dict() for w in weeks])

@bp.route('', methods=['POST'])
def create_week():
    data = request.get_json()
    week_start = date.fromisoformat(data['week_start_date'])
    existing = WeekPlan.query.filter_by(week_start_date=week_start).first()
    if existing:
        return jsonify({'error': 'Week plan already exists for this date'}), 409
    wp = WeekPlan(
        week_start_date=week_start,
        slots=data.get('slots', {}),
        notes=data.get('notes'),
    )
    db.session.add(wp)
    db.session.commit()
    return jsonify(wp.to_dict()), 201

@bp.route('/<int:week_id>', methods=['GET'])
def get_week(week_id):
    wp = WeekPlan.query.get_or_404(week_id)
    return jsonify(wp.to_dict())

@bp.route('/<int:week_id>', methods=['PUT'])
def update_week(week_id):
    wp = WeekPlan.query.get_or_404(week_id)
    data = request.get_json()
    if 'slots' in data:
        wp.slots = data['slots']
    if 'notes' in data:
        wp.notes = data['notes']
    db.session.commit()
    return jsonify(wp.to_dict())
```

- [ ] Write `tests/test_weeks_api.py`:

```python
from datetime import date

def test_list_weeks_empty(client):
    resp = client.get('/api/weeks')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_create_week(client):
    resp = client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['week_start_date'] == '2026-04-28'
    assert data['slots'] == {}

def test_create_week_duplicate(client):
    client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    resp = client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    assert resp.status_code == 409

def test_get_week(client):
    create_resp = client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    week_id = create_resp.get_json()['id']
    resp = client.get(f'/api/weeks/{week_id}')
    assert resp.status_code == 200
    assert resp.get_json()['week_start_date'] == '2026-04-28'

def test_update_week_slots(client):
    create_resp = client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    week_id = create_resp.get_json()['id']
    resp = client.put(f'/api/weeks/{week_id}', json={'slots': {'mon_dinner': 1}})
    assert resp.status_code == 200
    assert resp.get_json()['slots']['mon_dinner'] == 1
```

- [ ] Run `pytest tests/test_weeks_api.py -v` — expect PASS (output contains `5 passed`)
- [ ] `git commit -m "feat: week plan CRUD API"`

---

### Task 8: Suggestion Service

**Files:**
- Create: `app/services/suggestion_service.py`
- Modify: `app/api/weeks.py`
- Test: `tests/test_suggestion_service.py`

- [ ] Write failing test `tests/test_suggestion_service.py`
- [ ] Run `pytest tests/test_suggestion_service.py -v` — expect FAIL (service doesn't exist yet)
- [ ] Create `app/services/suggestion_service.py`:

```python
import random
from datetime import date, timedelta
from app.models.recipe import Recipe
from app.models.preference import Preference

VALID_METHODS = {'oven', 'stove', 'grill', 'air_fryer'}

# Slot key → (day_index 0=Mon, meal_type)
SLOT_META = {
    'mon_lunch': (0, 'lunch'), 'mon_dinner': (0, 'dinner'),
    'tue_lunch': (1, 'lunch'), 'tue_dinner': (1, 'dinner'),
    'wed_lunch': (2, 'lunch'), 'wed_dinner': (2, 'dinner'),
    'thu_lunch': (3, 'lunch'), 'thu_dinner': (3, 'dinner'),
    'fri_lunch': (4, 'lunch'), 'fri_dinner': (4, 'dinner'),
    'sunday_prep': (6, 'prep'),
}

# Maps dinner slot key → next-day lunch key
LEFTOVER_PAIRS = {
    'mon_dinner': 'tue_lunch',
    'tue_dinner': 'wed_lunch',
    'wed_dinner': 'thu_lunch',
    'thu_dinner': 'fri_lunch',
}


def suggest_slots(week_plan):
    """Return updated slots dict with suggestions for all empty slots."""
    slots = dict(week_plan.slots or {})
    preferences = Preference.query.all()
    three_weeks_ago = date.today() - timedelta(weeks=3)

    recently_used = {
        r.id for r in Recipe.query.filter(
            Recipe.last_used_date >= three_weeks_ago
        ).all()
    }

    available = [
        r for r in Recipe.query.all()
        if r.cook_method
        and any(m in VALID_METHODS for m in r.cook_method)
        and r.id not in recently_used
    ]

    likes = {p.value.lower() for p in preferences if p.type == 'like'}
    dislikes = {p.value.lower() for p in preferences if p.type == 'dislike'}

    def score(recipe):
        s = 1.0
        terms = {recipe.name.lower()}
        for ing in (recipe.ingredients or []):
            terms.add(ing.get('name', '').lower())
        for tag in (recipe.tags or []):
            terms.add(tag.lower())
        for like in likes:
            if any(like in t for t in terms):
                s += 0.5
        for dislike in dislikes:
            if any(dislike in t for t in terms):
                s -= 2.0
        return max(s, 0.01)

    def pick(candidates):
        if not candidates:
            return None
        weights = [score(r) for r in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    for slot_key in list(SLOT_META.keys()):
        if slots.get(slot_key):
            continue

        _, meal_type = SLOT_META[slot_key]

        if meal_type == 'prep':
            batch_pool = [r for r in available if 'batch' in (r.tags or [])]
            recipe = pick(batch_pool) or pick(available)
        elif meal_type == 'lunch':
            # Check if previous dinner suggests leftovers
            prev_dinner = next(
                (d for d, l in LEFTOVER_PAIRS.items() if l == slot_key), None
            )
            if prev_dinner and slots.get(prev_dinner):
                val = str(slots[prev_dinner])
                if not val.startswith('leftover:'):
                    recipe_id = int(val)
                    dinner_recipe = Recipe.query.get(recipe_id)
                    if dinner_recipe and dinner_recipe.makes_leftovers:
                        slots[slot_key] = f'leftover:{recipe_id}'
                        continue
            recipe = pick(available)
        else:
            recipe = pick(available)

        if recipe:
            slots[slot_key] = recipe.id

    return slots
```

- [ ] Append suggest endpoint to `app/api/weeks.py`:

```python
@bp.route('/<int:week_id>/suggest', methods=['POST'])
def suggest(week_id):
    wp = WeekPlan.query.get_or_404(week_id)
    from app.services.suggestion_service import suggest_slots
    wp.slots = suggest_slots(wp)
    db.session.commit()
    return jsonify(wp.to_dict())
```

- [ ] Write `tests/test_suggestion_service.py`:

```python
from datetime import date, timedelta
from app.models.recipe import Recipe
from app.models.week_plan import WeekPlan
from app.services.suggestion_service import suggest_slots

def make_recipe(db, name, cook_method=None, makes_leftovers=False, tags=None):
    r = Recipe(
        name=name,
        base_servings=2,
        cook_method=cook_method or ['stove'],
        makes_leftovers=makes_leftovers,
        tags=tags or [],
    )
    db.session.add(r)
    db.session.commit()
    return r

def test_suggest_fills_empty_slots(app, db):
    with app.app_context():
        r1 = make_recipe(db, 'Pasta', cook_method=['stove'])
        r2 = make_recipe(db, 'Chicken', cook_method=['oven'])
        r3 = make_recipe(db, 'Steak', cook_method=['grill'])
        r4 = make_recipe(db, 'Salmon', cook_method=['air_fryer'])
        r5 = make_recipe(db, 'Tacos', cook_method=['stove'])
        r6 = make_recipe(db, 'Soup', cook_method=['stove'])
        r7 = make_recipe(db, 'Pizza', cook_method=['oven'])
        r8 = make_recipe(db, 'Stir Fry', cook_method=['stove'])
        r9 = make_recipe(db, 'Roast', cook_method=['oven'])
        r10 = make_recipe(db, 'Salad', cook_method=['stove'])
        wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={})
        db.session.add(wp)
        db.session.commit()
        result = suggest_slots(wp)
        assert result.get('mon_dinner') is not None
        assert result.get('fri_dinner') is not None

def test_suggest_skips_untagged_recipes(app, db):
    with app.app_context():
        untagged = Recipe(name='Microwave Meal', base_servings=2, cook_method=[])
        tagged = Recipe(name='Oven Chicken', base_servings=2, cook_method=['oven'])
        db.session.add_all([untagged, tagged])
        db.session.commit()
        wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={})
        db.session.add(wp)
        db.session.commit()
        result = suggest_slots(wp)
        for val in result.values():
            if val and not str(val).startswith('leftover:'):
                assert int(val) != untagged.id

def test_suggest_leftover_autofill(app, db):
    with app.app_context():
        r = make_recipe(db, 'Big Batch Pasta', cook_method=['stove'], makes_leftovers=True)
        # Fill remaining slots with other recipes so suggestions have candidates
        for i in range(10):
            make_recipe(db, f'Recipe {i}', cook_method=['oven'])
        wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={'mon_dinner': r.id})
        db.session.add(wp)
        db.session.commit()
        result = suggest_slots(wp)
        assert result.get('tue_lunch') == f'leftover:{r.id}'

def test_suggest_sunday_prep_uses_batch_tag(app, db):
    with app.app_context():
        batch = make_recipe(db, 'Batch Chili', cook_method=['stove'], tags=['batch'])
        normal = make_recipe(db, 'Quick Pasta', cook_method=['stove'])
        wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={})
        db.session.add(wp)
        db.session.commit()
        results = [suggest_slots(wp).get('sunday_prep') for _ in range(20)]
        # batch recipe should be selected when available
        assert batch.id in results
```

- [ ] Run `pytest tests/test_suggestion_service.py -v` — expect PASS (output contains `4 passed`)
- [ ] `git commit -m "feat: suggestion service and /suggest endpoint"`

---

### Task 9: Shopping Service

**Files:**
- Create: `app/services/shopping_service.py`
- Modify: `app/api/weeks.py`
- Test: `tests/test_shopping_service.py`

- [ ] Write failing test `tests/test_shopping_service.py`
- [ ] Run `pytest tests/test_shopping_service.py -v` — expect FAIL (service doesn't exist yet)
- [ ] Create `app/services/shopping_service.py`:

```python
from datetime import datetime
from app.database import db
from app.models.recipe import Recipe
from app.models.shopping_list import ShoppingList
from app.models.pantry_staple import PantryStaple


def generate_shopping_list(week_plan):
    """Aggregate ingredients from all slots, exclude pantry staples, upsert ShoppingList."""
    staple_names = {s.ingredient_name.lower() for s in PantryStaple.query.all()}
    aggregated = {}

    for slot_key, val in (week_plan.slots or {}).items():
        if not val:
            continue
        val_str = str(val)
        if val_str.startswith('leftover:'):
            continue  # dinner slot already counted

        recipe_id = int(val_str)
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            continue

        if slot_key == 'sunday_prep' or recipe.makes_leftovers:
            target = 4
        else:
            target = 2

        base = recipe.base_servings or 2
        scale = target / base

        for ing in (recipe.ingredients or []):
            name = ing.get('name', '').strip().lower()
            if not name:
                continue
            qty = ing.get('quantity') or 0
            unit = ing.get('unit', '') or ''
            category = ing.get('category', 'other') or 'other'

            if name not in aggregated:
                aggregated[name] = {
                    'quantity': 0,
                    'unit': unit,
                    'category': category,
                    'checked': False,
                    'is_staple': False,
                }
            if aggregated[name]['unit'] == unit:
                try:
                    aggregated[name]['quantity'] += float(qty) * scale
                except (TypeError, ValueError):
                    pass

    # Remove staples
    items = {name: data for name, data in aggregated.items() if name not in staple_names}

    existing = ShoppingList.query.filter_by(week_plan_id=week_plan.id).first()
    if existing:
        existing.items = items
        existing.generated_at = datetime.utcnow()
        db.session.commit()
        return existing

    sl = ShoppingList(week_plan_id=week_plan.id, items=items, generated_at=datetime.utcnow())
    db.session.add(sl)
    db.session.commit()
    return sl
```

- [ ] Append shopping-list endpoints to `app/api/weeks.py`:

```python
@bp.route('/<int:week_id>/shopping-list', methods=['POST'])
def generate_shopping_list(week_id):
    wp = WeekPlan.query.get_or_404(week_id)
    from app.services.shopping_service import generate_shopping_list as _generate
    sl = _generate(wp)
    return jsonify(sl.to_dict()), 201

@bp.route('/<int:week_id>/shopping-list', methods=['GET'])
def get_shopping_list(week_id):
    wp = WeekPlan.query.get_or_404(week_id)
    sl = ShoppingList.query.filter_by(week_plan_id=week_id).first()
    if not sl:
        return jsonify(None)
    return jsonify(sl.to_dict())
```

- [ ] Write `tests/test_shopping_service.py`:

```python
from datetime import date
from app.models.recipe import Recipe
from app.models.week_plan import WeekPlan
from app.models.pantry_staple import PantryStaple
from app.services.shopping_service import generate_shopping_list


def make_recipe(db, name, ingredients, base_servings=2, makes_leftovers=False):
    r = Recipe(name=name, base_servings=base_servings, ingredients=ingredients,
               cook_method=['stove'], makes_leftovers=makes_leftovers)
    db.session.add(r)
    db.session.commit()
    return r


def test_shopping_list_aggregates_ingredients(app, db):
    with app.app_context():
        r = make_recipe(db, 'Pasta', [
            {'name': 'pasta', 'quantity': 200, 'unit': 'g', 'category': 'pantry'},
            {'name': 'tomato', 'quantity': 2, 'unit': 'cups', 'category': 'produce'},
        ], base_servings=2)
        wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={'mon_dinner': r.id})
        db.session.add(wp)
        db.session.commit()
        sl = generate_shopping_list(wp)
        assert 'pasta' in sl.items
        assert sl.items['pasta']['quantity'] == 200.0  # base 2, target 2 => scale 1

def test_shopping_list_scales_leftovers(app, db):
    with app.app_context():
        r = make_recipe(db, 'Big Pasta', [
            {'name': 'pasta', 'quantity': 200, 'unit': 'g', 'category': 'pantry'},
        ], base_servings=2, makes_leftovers=True)
        wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={'mon_dinner': r.id})
        db.session.add(wp)
        db.session.commit()
        sl = generate_shopping_list(wp)
        assert sl.items['pasta']['quantity'] == 400.0  # base 2, target 4 => scale 2

def test_shopping_list_skips_leftover_slots(app, db):
    with app.app_context():
        r = make_recipe(db, 'Pasta', [
            {'name': 'pasta', 'quantity': 200, 'unit': 'g', 'category': 'pantry'},
        ], base_servings=2, makes_leftovers=True)
        wp = WeekPlan(
            week_start_date=date(2026, 4, 28),
            slots={'mon_dinner': r.id, 'tue_lunch': f'leftover:{r.id}'}
        )
        db.session.add(wp)
        db.session.commit()
        sl = generate_shopping_list(wp)
        # pasta appears once (from mon_dinner), NOT doubled
        assert sl.items['pasta']['quantity'] == 400.0

def test_shopping_list_excludes_pantry_staples(app, db):
    with app.app_context():
        staple = PantryStaple(ingredient_name='salt', category='pantry')
        db.session.add(staple)
        r = make_recipe(db, 'Pasta', [
            {'name': 'pasta', 'quantity': 200, 'unit': 'g', 'category': 'pantry'},
            {'name': 'salt', 'quantity': 1, 'unit': 'tsp', 'category': 'pantry'},
        ], base_servings=2)
        wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={'mon_dinner': r.id})
        db.session.add(wp)
        db.session.commit()
        sl = generate_shopping_list(wp)
        assert 'salt' not in sl.items
        assert 'pasta' in sl.items

def test_shopping_list_regenerate_overwrites(app, db):
    with app.app_context():
        r = make_recipe(db, 'Pasta', [
            {'name': 'pasta', 'quantity': 200, 'unit': 'g', 'category': 'pantry'},
        ], base_servings=2)
        wp = WeekPlan(week_start_date=date(2026, 4, 28), slots={'mon_dinner': r.id})
        db.session.add(wp)
        db.session.commit()
        sl1 = generate_shopping_list(wp)
        wp.slots = {}
        db.session.commit()
        sl2 = generate_shopping_list(wp)
        assert sl1.id == sl2.id  # same record, overwritten
        assert sl2.items == {}
```

- [ ] Run `pytest tests/test_shopping_service.py -v` — expect PASS (output contains `5 passed`)
- [ ] `git commit -m "feat: shopping service and /shopping-list endpoint"`

---

### Task 10: Export Service

**Files:**
- Create: `app/services/export_service.py`
- Modify: `app/api/weeks.py`
- Test: `tests/test_export_service.py`

- [ ] Write failing test `tests/test_export_service.py`
- [ ] Run `pytest tests/test_export_service.py -v` — expect FAIL (service doesn't exist yet)
- [ ] Create `app/services/export_service.py`:

```python
CATEGORY_ORDER = ['produce', 'protein', 'dairy', 'pantry', 'other']


def render_markdown(shopping_list, week_plan):
    """Return Obsidian-ready markdown shopping list string."""
    week_start = week_plan.week_start_date
    if hasattr(week_start, 'strftime'):
        date_str = week_start.strftime('%b %-d, %Y')
    else:
        date_str = str(week_start)

    lines = [f'# Shopping List — Week of {date_str}', '']
    items = shopping_list.items or {}

    by_category = {}
    for name, data in items.items():
        cat = data.get('category', 'other') or 'other'
        by_category.setdefault(cat, []).append((name, data))

    all_cats = list(CATEGORY_ORDER)
    for cat in by_category:
        if cat not in all_cats:
            all_cats.append(cat)

    for cat in all_cats:
        if cat not in by_category:
            continue
        lines.append(f'## {cat.capitalize()}')
        for name, data in sorted(by_category[cat]):
            qty = data.get('quantity', '')
            unit = data.get('unit', '') or ''
            if qty and unit:
                lines.append(f'- [ ] {name} — {float(qty):.1f} {unit}')
            elif qty:
                lines.append(f'- [ ] {name} — {float(qty):.1f}')
            else:
                lines.append(f'- [ ] {name}')
        lines.append('')

    return '\n'.join(lines)
```

- [ ] Append export endpoint to `app/api/weeks.py`:

```python
@bp.route('/<int:week_id>/export', methods=['GET'])
def export_markdown(week_id):
    wp = WeekPlan.query.get_or_404(week_id)
    sl = ShoppingList.query.filter_by(week_plan_id=week_id).first()
    if not sl:
        return jsonify({'error': 'No shopping list for this week. Generate one first.'}), 404
    from app.services.export_service import render_markdown
    md = render_markdown(sl, wp)
    return md, 200, {'Content-Type': 'text/plain; charset=utf-8'}
```

- [ ] Write `tests/test_export_service.py`:

```python
from datetime import date
from app.models.week_plan import WeekPlan
from app.models.shopping_list import ShoppingList
from app.services.export_service import render_markdown


def test_render_markdown_basic():
    wp = WeekPlan.__new__(WeekPlan)
    wp.week_start_date = date(2026, 4, 28)
    sl = ShoppingList.__new__(ShoppingList)
    sl.items = {
        'chicken breast': {'quantity': 1.5, 'unit': 'lbs', 'category': 'protein', 'checked': False, 'is_staple': False},
        'spinach': {'quantity': 2.0, 'unit': 'cups', 'category': 'produce', 'checked': False, 'is_staple': False},
    }
    result = render_markdown(sl, wp)
    assert '# Shopping List — Week of Apr 28, 2026' in result
    assert '## Produce' in result
    assert '## Protein' in result
    assert '- [ ] spinach — 2.0 cups' in result
    assert '- [ ] chicken breast — 1.5 lbs' in result
    # Produce should appear before Protein
    assert result.index('## Produce') < result.index('## Protein')


def test_render_markdown_empty():
    wp = WeekPlan.__new__(WeekPlan)
    wp.week_start_date = date(2026, 4, 28)
    sl = ShoppingList.__new__(ShoppingList)
    sl.items = {}
    result = render_markdown(sl, wp)
    assert '# Shopping List' in result
    assert '## Produce' not in result
```

- [ ] Run `pytest tests/test_export_service.py -v` — expect PASS (output contains `2 passed`)
- [ ] `git commit -m "feat: markdown export service and /export endpoint"`

---

### Task 11: Google Calendar Service

**Files:**
- Create: `app/services/calendar_service.py`
- Modify: `app/api/weeks.py`

> **Before using calendar sync:** (1) Go to console.cloud.google.com → New Project. (2) Enable Google Calendar API. (3) OAuth consent screen → External → add your Gmail as test user. (4) Credentials → OAuth 2.0 Client ID → Desktop App → download JSON → save as `data/credentials.json`. The first `sync-calendar` request will open a browser for OAuth — token saved to `data/token.json` automatically.

- [ ] Create `app/services/calendar_service.py`:

```python
import os
from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'data', 'credentials.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'data', 'token.json')

# Map slot key prefix to day offset from Monday (0=Mon)
DAY_OFFSETS = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sunday': 6}


def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def find_calendar_id(service, calendar_name):
    calendars = service.calendarList().list().execute()
    for cal in calendars.get('items', []):
        if cal['summary'] == calendar_name:
            return cal['id']
    return None


def sync_week(week_plan, slots_with_recipes, config):
    """
    Create Google Calendar events for each filled slot.
    slots_with_recipes: dict of {slot_key: Recipe object}
    config: object with LUNCH_START, DINNER_START, SUNDAY_PREP_START, CALENDAR_NAME, CALENDAR_TIMEZONE
    """
    service = get_calendar_service()
    calendar_id = find_calendar_id(service, config.CALENDAR_NAME)
    if not calendar_id:
        raise ValueError(f"Calendar '{config.CALENDAR_NAME}' not found in your Google account")

    tz = pytz.timezone(config.CALENDAR_TIMEZONE)
    week_start = week_plan.week_start_date

    for slot_key, recipe in slots_with_recipes.items():
        if not recipe:
            continue

        # Parse slot key: e.g. 'mon_dinner', 'sunday_prep'
        if slot_key == 'sunday_prep':
            day_key = 'sunday'
            start_time_str = config.SUNDAY_PREP_START
        elif slot_key.endswith('_lunch'):
            day_key = slot_key[:-6]  # strip '_lunch'
            start_time_str = config.LUNCH_START
        elif slot_key.endswith('_dinner'):
            day_key = slot_key[:-7]  # strip '_dinner'
            start_time_str = config.DINNER_START
        else:
            continue

        day_offset = DAY_OFFSETS.get(day_key)
        if day_offset is None:
            continue

        from datetime import date as _date, timedelta as _td
        event_date = week_start + _td(days=day_offset)
        h, m = map(int, start_time_str.split(':'))
        start_dt = tz.localize(datetime(event_date.year, event_date.month, event_date.day, h, m))
        duration_mins = (recipe.prep_time_mins or 0) + (recipe.cook_time_mins or 0)
        if duration_mins == 0:
            duration_mins = 60
        end_dt = start_dt + timedelta(minutes=duration_mins)

        event = {
            'summary': recipe.name,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': config.CALENDAR_TIMEZONE},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': config.CALENDAR_TIMEZONE},
        }
        service.events().insert(calendarId=calendar_id, body=event).execute()
```

- [ ] Append sync-calendar endpoint to `app/api/weeks.py`:

```python
@bp.route('/<int:week_id>/sync-calendar', methods=['POST'])
def sync_calendar(week_id):
    wp = WeekPlan.query.get_or_404(week_id)
    import config as cfg

    slots_with_recipes = {}
    for slot_key, val in (wp.slots or {}).items():
        if not val:
            continue
        val_str = str(val)
        if val_str.startswith('leftover:'):
            recipe_id = int(val_str.split(':')[1])
        else:
            recipe_id = int(val_str)
        slots_with_recipes[slot_key] = Recipe.query.get(recipe_id)

    try:
        from app.services.calendar_service import sync_week
        sync_week(wp, slots_with_recipes, cfg)
        wp.calendar_synced = True
        db.session.commit()
        return jsonify({'synced': True})
    except FileNotFoundError:
        return jsonify({'error': 'credentials.json not found at data/credentials.json — see Google Cloud setup instructions'}), 503
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Calendar sync failed: {str(e)}'}), 500
```

No automated tests for this service (requires live OAuth). Manual verification steps:
1. Run `python run.py`
2. Create a week plan with at least one recipe slot
3. Click "Sync to Calendar" in the UI
4. Browser opens Google OAuth flow — authorize
5. Check "Tripe F" calendar for the events
6. Verify event times match LUNCH_START / DINNER_START config

- [ ] `git commit -m "feat: Google Calendar sync service and /sync-calendar endpoint"`

---

### Task 12: Frontend Shell

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/style.css`
- Create: `app/static/app.js`

- [ ] Create `app/static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Meal Planner</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav class="top-nav">
    <span class="app-title">Meal Planner</span>
    <div class="nav-tabs">
      <button class="nav-tab active" data-view="planner">Planner</button>
      <button class="nav-tab" data-view="recipes">Recipes</button>
      <button class="nav-tab" data-view="shopping">Shopping</button>
      <button class="nav-tab" data-view="settings">Settings</button>
    </div>
  </nav>

  <main>
    <div id="view-planner" class="view active"></div>
    <div id="view-recipes" class="view"></div>
    <div id="view-shopping" class="view"></div>
    <div id="view-settings" class="view"></div>
  </main>

  <div id="modal-overlay" class="modal-overlay hidden">
    <div id="modal-box" class="modal-box"></div>
  </div>

  <div id="error-banner" class="error-banner hidden"></div>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] Create `app/static/style.css`:

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f5f5f5;
  color: #222;
}

.top-nav {
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 0.75rem 1.5rem;
  background: #1a1a2e;
  color: #fff;
}

.app-title { font-weight: 700; font-size: 1.1rem; }

.nav-tabs { display: flex; gap: 0.25rem; }

.nav-tab {
  padding: 0.4rem 1rem;
  border: none;
  background: transparent;
  color: #ccc;
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.9rem;
}

.nav-tab:hover { background: rgba(255,255,255,0.1); color: #fff; }
.nav-tab.active { background: rgba(255,255,255,0.2); color: #fff; font-weight: 600; }

main { padding: 1.5rem; max-width: 1200px; margin: 0 auto; }

.view { display: none; }
.view.active { display: block; }

.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.modal-overlay.hidden { display: none; }

.modal-box {
  background: #fff;
  border-radius: 8px;
  padding: 1.5rem;
  width: 90%;
  max-width: 560px;
  max-height: 80vh;
  overflow-y: auto;
}

.error-banner {
  position: fixed;
  bottom: 1rem; left: 50%;
  transform: translateX(-50%);
  background: #c0392b;
  color: #fff;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  z-index: 200;
  cursor: pointer;
}
.error-banner.hidden { display: none; }

button { cursor: pointer; }

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 500;
}
.btn-primary { background: #1a1a2e; color: #fff; }
.btn-primary:hover { background: #2d2d4e; }
.btn-secondary { background: #e0e0e0; color: #333; }
.btn-secondary:hover { background: #ccc; }
.btn-danger { background: #c0392b; color: #fff; }
.btn-danger:hover { background: #962d22; }
.btn-sm { padding: 0.25rem 0.6rem; font-size: 0.8rem; }
```

- [ ] Create `app/static/app.js`:

```javascript
// ── Router ──────────────────────────────────────────────────────────────────
const views = ['planner', 'recipes', 'shopping', 'settings'];

function navigate(viewName) {
  views.forEach(v => {
    document.getElementById(`view-${v}`).classList.toggle('active', v === viewName);
    document.querySelector(`.nav-tab[data-view="${v}"]`).classList.toggle('active', v === viewName);
  });
  if (viewName === 'planner') renderPlanner();
  if (viewName === 'recipes') renderRecipes();
  if (viewName === 'shopping') renderShopping();
  if (viewName === 'settings') renderSettings();
}

document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => navigate(tab.dataset.view));
});

// ── API helpers ──────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const resp = await fetch(`/api${path}`, opts);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(err.error || `HTTP ${resp.status}`);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function showError(msg) {
  const banner = document.getElementById('error-banner');
  banner.textContent = msg + ' (click to dismiss)';
  banner.classList.remove('hidden');
  banner.onclick = () => banner.classList.add('hidden');
}

// ── Modal ────────────────────────────────────────────────────────────────────
function openModal(html) {
  document.getElementById('modal-box').innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});

// ── View stubs (filled in subsequent tasks) ─────────────────────────────────
function renderPlanner() {
  document.getElementById('view-planner').innerHTML = '<p>Planner loading...</p>';
}
function renderRecipes() {
  document.getElementById('view-recipes').innerHTML = '<p>Recipes loading...</p>';
}
function renderShopping() {
  document.getElementById('view-shopping').innerHTML = '<p>Shopping loading...</p>';
}
function renderSettings() {
  document.getElementById('view-settings').innerHTML = '<p>Settings loading...</p>';
}

// ── Init ─────────────────────────────────────────────────────────────────────
navigate('planner');
```

Manual verification:
1. `python run.py`
2. Open `http://localhost:5000`
3. Verify four nav tabs render and clicking each switches the view
4. Verify error banner is hidden by default

- [ ] `git commit -m "feat: frontend shell — nav, router, modal, error banner"`

---

### Task 13: Meal Planner View

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`

- [ ] Add state object near top of `app/static/app.js` (after the `views` declaration):

```javascript
const state = { currentWeekId: null, weeks: [], recipes: [] };
```

- [ ] Replace the `renderPlanner` stub in `app/static/app.js` with the complete implementation:

```javascript
async function renderPlanner() {
  const el = document.getElementById('view-planner');
  el.innerHTML = '<p>Loading...</p>';
  try {
    state.weeks = await api('GET', '/weeks');
    state.recipes = await api('GET', '/recipes');
    if (state.weeks.length === 0) {
      el.innerHTML = plannerEmptyHTML();
      document.getElementById('btn-new-week').onclick = createNewWeek;
      return;
    }
    if (!state.currentWeekId) state.currentWeekId = state.weeks[0].id;
    const week = state.weeks.find(w => w.id === state.currentWeekId) || state.weeks[0];
    el.innerHTML = plannerHTML(week);
    bindPlannerEvents(week);
  } catch (e) { showError(e.message); }
}

function plannerEmptyHTML() {
  return `<div style="text-align:center;padding:3rem">
    <p style="margin-bottom:1rem;color:#666">No weeks yet.</p>
    <button class="btn btn-primary" id="btn-new-week">Create First Week</button>
  </div>`;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri'];
const MEAL_KEYS = ['lunch', 'dinner'];

function plannerHTML(week) {
  const weekLabel = new Date(week.week_start_date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const prevWeek = state.weeks.find(w => w.id < week.id);
  const nextWeek = state.weeks.find(w => w.id > week.id);

  let rows = '';
  MEAL_KEYS.forEach(meal => {
    rows += `<tr><th>${meal.charAt(0).toUpperCase() + meal.slice(1)}</th>`;
    DAY_KEYS.forEach(day => {
      const slotKey = `${day}_${meal}`;
      const val = week.slots[slotKey];
      rows += `<td class="planner-cell" data-slot="${slotKey}">${cellContent(val)}</td>`;
    });
    rows += '</tr>';
  });

  const sundayVal = week.slots['sunday_prep'];
  const sunday_synced = week.calendar_synced ? ' (synced)' : '';

  return `
    <div class="planner-header">
      <button class="btn btn-secondary btn-sm" id="btn-prev" ${!prevWeek ? 'disabled' : ''}>← Prev</button>
      <span class="week-label">Week of ${weekLabel}</span>
      <button class="btn btn-secondary btn-sm" id="btn-next" ${!nextWeek ? 'disabled' : ''}>Next →</button>
      <button class="btn btn-primary btn-sm" id="btn-new-week">+ New Week</button>
    </div>
    <table class="planner-grid">
      <thead><tr><th></th>${DAYS.map(d => `<th>${d}</th>`).join('')}</tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="planner-sunday">
      <strong>Sunday Prep:</strong>
      <span class="planner-cell" data-slot="sunday_prep">${cellContent(sundayVal)}</span>
    </div>
    <div class="planner-actions">
      <button class="btn btn-secondary" id="btn-suggest">Suggest</button>
      <button class="btn btn-secondary" id="btn-gen-shopping">Generate Shopping List</button>
      <button class="btn btn-secondary" id="btn-sync-cal">Sync to Calendar${sunday_synced}</button>
    </div>`;
}

function cellContent(val) {
  if (!val) return '<span class="cell-empty">—</span>';
  if (typeof val === 'string' && val.startsWith('leftover:')) return '<span class="cell-leftover">↩ Leftovers</span>';
  const recipe = state.recipes.find(r => r.id === (typeof val === 'string' ? parseInt(val) : val));
  if (!recipe) return '<span class="cell-empty">—</span>';
  const methods = (recipe.cook_method || []).join(', ');
  return `<span class="cell-recipe" title="${methods}">${recipe.name}</span>`;
}

function bindPlannerEvents(week) {
  document.getElementById('btn-prev')?.addEventListener('click', () => {
    const prev = state.weeks.find(w => w.id < week.id);
    if (prev) { state.currentWeekId = prev.id; renderPlanner(); }
  });
  document.getElementById('btn-next')?.addEventListener('click', () => {
    const next = state.weeks.find(w => w.id > week.id);
    if (next) { state.currentWeekId = next.id; renderPlanner(); }
  });
  document.getElementById('btn-new-week').addEventListener('click', createNewWeek);
  document.getElementById('btn-suggest').addEventListener('click', async () => {
    try {
      const updated = await api('POST', `/weeks/${week.id}/suggest`);
      state.currentWeekId = updated.id;
      renderPlanner();
    } catch (e) { showError(e.message); }
  });
  document.getElementById('btn-gen-shopping').addEventListener('click', async () => {
    try {
      await api('POST', `/weeks/${week.id}/shopping-list`);
      navigate('shopping');
    } catch (e) { showError(e.message); }
  });
  document.getElementById('btn-sync-cal').addEventListener('click', async () => {
    try {
      await api('POST', `/weeks/${week.id}/sync-calendar`);
      renderPlanner();
    } catch (e) { showError(e.message); }
  });
  document.querySelectorAll('.planner-cell[data-slot]').forEach(cell => {
    cell.addEventListener('click', () => openRecipePicker(week, cell.dataset.slot));
  });
}

async function createNewWeek() {
  const today = new Date();
  const dayOfWeek = today.getDay();
  const daysToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(today);
  monday.setDate(today.getDate() + daysToMonday);
  const iso = monday.toISOString().split('T')[0];
  try {
    const week = await api('POST', '/weeks', { week_start_date: iso });
    state.weeks.unshift(week);
    state.currentWeekId = week.id;
    renderPlanner();
  } catch (e) { showError(e.message); }
}

function openRecipePicker(week, slotKey) {
  const items = state.recipes.map(r =>
    `<div class="recipe-pick-item" data-id="${r.id}">${r.name} <small>${(r.cook_method||[]).join(', ')}</small></div>`
  ).join('') || '<p>No recipes in library yet.</p>';

  openModal(`
    <h3 style="margin-bottom:1rem">Pick a recipe for ${slotKey.replace('_', ' ')}</h3>
    <input id="picker-search" class="picker-search" placeholder="Search..." style="width:100%;margin-bottom:0.75rem;padding:0.4rem">
    <div id="picker-list">${items}</div>
    <button class="btn btn-secondary btn-sm" style="margin-top:0.75rem" id="btn-clear-slot">Clear slot</button>
  `);

  document.getElementById('picker-search').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('.recipe-pick-item').forEach(el => {
      el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });

  document.querySelectorAll('.recipe-pick-item').forEach(el => {
    el.addEventListener('click', async () => {
      const newSlots = { ...week.slots, [slotKey]: parseInt(el.dataset.id) };
      try {
        await api('PUT', `/weeks/${week.id}`, { slots: newSlots });
        closeModal();
        renderPlanner();
      } catch (e) { showError(e.message); }
    });
  });

  document.getElementById('btn-clear-slot').addEventListener('click', async () => {
    const newSlots = { ...week.slots };
    delete newSlots[slotKey];
    try {
      await api('PUT', `/weeks/${week.id}`, { slots: newSlots });
      closeModal();
      renderPlanner();
    } catch (e) { showError(e.message); }
  });
}
```

- [ ] Append to `app/static/style.css`:

```css
.planner-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.week-label { font-weight: 600; font-size: 1.05rem; flex: 1; text-align: center; }

.planner-grid { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
.planner-grid th, .planner-grid td {
  border: 1px solid #ddd;
  padding: 0.5rem;
  text-align: center;
  min-width: 120px;
}
.planner-grid th { background: #f0f0f0; font-weight: 600; }
.planner-grid td { background: #fff; cursor: pointer; }
.planner-grid td:hover { background: #f9f9f9; }

.cell-empty { color: #aaa; font-style: italic; }
.cell-recipe { font-weight: 500; }
.cell-leftover { color: #888; font-style: italic; }

.planner-sunday { margin-bottom: 1rem; padding: 0.5rem; background: #fff; border: 1px solid #ddd; border-radius: 4px; }
.planner-sunday .planner-cell { cursor: pointer; margin-left: 0.5rem; }

.planner-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }

.recipe-pick-item {
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  border-radius: 4px;
  border-bottom: 1px solid #eee;
}
.recipe-pick-item:hover { background: #f0f0f0; }
.recipe-pick-item small { color: #888; margin-left: 0.5rem; }
```

Manual verification:
1. `python run.py` → open http://localhost:5000
2. "Create First Week" creates a week with the upcoming Monday
3. Clicking a cell opens the recipe picker modal
4. "Suggest" fills empty slots
5. "Generate Shopping List" navigates to shopping view

- [ ] `git commit -m "feat: meal planner view — grid, slot picker, suggest, shopping trigger"`

---

### Task 14: Recipe Library View

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`

- [ ] Replace the `renderRecipes` stub in `app/static/app.js` with the complete implementation:

```javascript
async function renderRecipes() {
  const el = document.getElementById('view-recipes');
  el.innerHTML = '<p>Loading...</p>';
  try {
    state.recipes = await api('GET', '/recipes');
    el.innerHTML = recipesHTML(state.recipes);
    bindRecipesEvents();
  } catch (e) { showError(e.message); }
}

function recipesHTML(recipes) {
  const rows = recipes.length === 0
    ? '<tr><td colspan="5" style="text-align:center;color:#888;padding:2rem">No recipes yet. Add one above.</td></tr>'
    : recipes.map(r => `
      <tr>
        <td>${r.name}</td>
        <td>${(r.cook_method || []).join(', ') || '—'}</td>
        <td>${(r.tags || []).join(', ') || '—'}</td>
        <td>${r.last_used_date || 'never'}</td>
        <td>
          <button class="btn btn-secondary btn-sm" data-action="edit" data-id="${r.id}">Edit</button>
          <button class="btn btn-danger btn-sm" data-action="delete" data-id="${r.id}">Delete</button>
        </td>
      </tr>`).join('');

  return `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
      <h2>Recipe Library</h2>
      <div style="display:flex;gap:0.5rem">
        <button class="btn btn-primary" id="btn-add-recipe">+ Add Recipe</button>
        <button class="btn btn-secondary" id="btn-import-url">Import from URL</button>
      </div>
    </div>
    <table class="recipe-table">
      <thead><tr><th>Name</th><th>Method</th><th>Tags</th><th>Last Used</th><th>Actions</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function bindRecipesEvents() {
  document.getElementById('btn-add-recipe').addEventListener('click', () => openRecipeForm(null));
  document.getElementById('btn-import-url').addEventListener('click', openImportUrlModal);

  document.querySelectorAll('[data-action="edit"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const recipe = state.recipes.find(r => r.id === parseInt(btn.dataset.id));
      openRecipeForm(recipe);
    });
  });
  document.querySelectorAll('[data-action="delete"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Delete this recipe?')) return;
      try {
        await api('DELETE', `/recipes/${btn.dataset.id}`);
        renderRecipes();
      } catch (e) { showError(e.message); }
    });
  });
}

function recipeFormHTML(recipe) {
  const r = recipe || {};
  return `
    <h3 style="margin-bottom:1rem">${r.id ? 'Edit Recipe' : 'Add Recipe'}</h3>
    <div class="form-grid">
      <label>Name*<input name="name" value="${r.name || ''}" required></label>
      <label>Source URL<input name="source_url" value="${r.source_url || ''}"></label>
      <label>Base Servings<input name="base_servings" type="number" min="1" value="${r.base_servings || 2}"></label>
      <label>Prep Time (mins)<input name="prep_time_mins" type="number" min="0" value="${r.prep_time_mins || ''}"></label>
      <label>Cook Time (mins)<input name="cook_time_mins" type="number" min="0" value="${r.cook_time_mins || ''}"></label>
      <label>Makes Leftovers
        <input name="makes_leftovers" type="checkbox" ${r.makes_leftovers ? 'checked' : ''}>
      </label>
    </div>
    <label>Cook Methods (check all that apply)</label>
    <div class="method-checks">
      ${['oven','stove','grill','air_fryer'].map(m =>
        `<label><input type="checkbox" name="cook_method" value="${m}" ${(r.cook_method||[]).includes(m) ? 'checked' : ''}> ${m.replace('_',' ')}</label>`
      ).join('')}
    </div>
    <label>Tags (comma-separated)<input name="tags" value="${(r.tags||[]).join(', ')}"></label>
    <label>Notes<textarea name="notes" rows="2">${r.notes || ''}</textarea></label>
    <label>Ingredients (one per line: name, quantity unit, category)<textarea name="ingredients_raw" rows="5">${(r.ingredients||[]).map(i => `${i.name}, ${i.quantity} ${i.unit}, ${i.category}`).join('\n')}</textarea></label>
    <div style="margin-top:1rem;display:flex;gap:0.5rem">
      <button class="btn btn-primary" id="btn-save-recipe">Save</button>
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    </div>`;
}

function openRecipeForm(recipe) {
  openModal(recipeFormHTML(recipe));
  document.getElementById('btn-save-recipe').addEventListener('click', async () => {
    const form = document.querySelector('#modal-box');
    const name = form.querySelector('[name="name"]').value.trim();
    if (!name) { alert('Name is required'); return; }

    const methods = [...form.querySelectorAll('[name="cook_method"]:checked')].map(el => el.value);
    const tagsRaw = form.querySelector('[name="tags"]').value;
    const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);
    const ingredientsRaw = form.querySelector('[name="ingredients_raw"]').value;
    const ingredients = ingredientsRaw.split('\n').map(line => {
      const parts = line.split(',').map(p => p.trim());
      const [name, qtyUnit, cat] = parts;
      if (!name) return null;
      const qpParts = (qtyUnit || '').split(' ');
      const qty = parseFloat(qpParts[0]) || '';
      const unit = qpParts.slice(1).join(' ') || '';
      return { name, quantity: qty, unit, category: cat || 'other' };
    }).filter(Boolean);

    const body = {
      name,
      source_url: form.querySelector('[name="source_url"]').value.trim() || null,
      base_servings: parseInt(form.querySelector('[name="base_servings"]').value) || 2,
      prep_time_mins: parseInt(form.querySelector('[name="prep_time_mins"]').value) || null,
      cook_time_mins: parseInt(form.querySelector('[name="cook_time_mins"]').value) || null,
      makes_leftovers: form.querySelector('[name="makes_leftovers"]').checked,
      cook_method: methods,
      tags,
      ingredients,
      notes: form.querySelector('[name="notes"]').value.trim() || null,
    };

    try {
      if (recipe?.id) {
        await api('PUT', `/recipes/${recipe.id}`, body);
      } else {
        await api('POST', '/recipes', body);
      }
      closeModal();
      renderRecipes();
    } catch (e) { showError(e.message); }
  });
}

function openImportUrlModal() {
  openModal(`
    <h3 style="margin-bottom:1rem">Import Recipe from URL</h3>
    <p style="color:#666;margin-bottom:0.75rem;font-size:0.9rem">Tries Spoonacular first, then JSON-LD (works with skinnytaste.com and most recipe blogs).</p>
    <input id="import-url-input" placeholder="https://..." style="width:100%;padding:0.5rem;margin-bottom:0.75rem">
    <button class="btn btn-primary" id="btn-do-import">Import</button>
    <span id="import-status" style="margin-left:0.75rem;color:#666"></span>
  `);
  document.getElementById('btn-do-import').addEventListener('click', async () => {
    const url = document.getElementById('import-url-input').value.trim();
    if (!url) return;
    document.getElementById('import-status').textContent = 'Fetching...';
    try {
      const data = await api('POST', '/recipes/import-url', { url });
      closeModal();
      openRecipeForm(data);  // prefill form with parsed data for review
    } catch (e) {
      document.getElementById('import-status').textContent = '';
      showError(e.message);
    }
  });
}
```

- [ ] Append to `app/static/style.css`:

```css
.recipe-table { width: 100%; border-collapse: collapse; }
.recipe-table th, .recipe-table td {
  border: 1px solid #ddd;
  padding: 0.5rem 0.75rem;
  text-align: left;
}
.recipe-table th { background: #f0f0f0; }
.recipe-table tr:hover td { background: #f9f9f9; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem 1rem; margin-bottom: 0.75rem; }
.form-grid label, label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.9rem; margin-bottom: 0.5rem; }
input, textarea, select { padding: 0.4rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9rem; }
textarea { resize: vertical; }

.method-checks { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
.method-checks label { flex-direction: row; align-items: center; gap: 0.3rem; margin: 0; }
```

Manual verification:
1. Add a recipe manually — all fields save correctly
2. Edit a recipe — changes persist
3. Delete a recipe — removed from table
4. Import from URL (skinnytaste.com link) — form pre-fills with parsed data

- [ ] `git commit -m "feat: recipe library view — CRUD, URL import, form"`

---

### Task 15: Shopping List View

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`

- [ ] Replace the `renderShopping` stub in `app/static/app.js` with the complete implementation:

```javascript
async function renderShopping() {
  const el = document.getElementById('view-shopping');
  el.innerHTML = '<p>Loading...</p>';
  try {
    state.weeks = await api('GET', '/weeks');
    if (state.weeks.length === 0) {
      el.innerHTML = '<p style="color:#888;padding:2rem">No weeks yet.</p>';
      return;
    }
    const weekId = state.currentWeekId || state.weeks[0].id;
    const week = state.weeks.find(w => w.id === weekId) || state.weeks[0];
    const sl = await api('GET', `/weeks/${week.id}/shopping-list`);
    el.innerHTML = shoppingHTML(week, sl);
    bindShoppingEvents(week, sl);
  } catch (e) { showError(e.message); }
}

const CAT_ORDER = ['produce', 'protein', 'dairy', 'pantry', 'other'];

function shoppingHTML(week, sl) {
  const weekLabel = new Date(week.week_start_date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  if (!sl || !sl.items || Object.keys(sl.items).length === 0) {
    return `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
      <h2>Shopping List — Week of ${weekLabel}</h2>
      <button class="btn btn-primary" id="btn-regen">Generate</button>
    </div>
    <p style="color:#888">No shopping list yet. Generate one from the Planner view.</p>`;
  }

  const items = sl.items;
  const byCat = {};
  for (const [name, data] of Object.entries(items)) {
    const cat = data.category || 'other';
    if (!byCat[cat]) byCat[cat] = [];
    byCat[cat].push([name, data]);
  }

  const allCats = [...CAT_ORDER, ...Object.keys(byCat).filter(c => !CAT_ORDER.includes(c))];
  let sections = '';
  for (const cat of allCats) {
    if (!byCat[cat]) continue;
    const catItems = byCat[cat].sort((a, b) => a[0].localeCompare(b[0]));
    sections += `<div class="shopping-section">
      <h3>${cat.charAt(0).toUpperCase() + cat.slice(1)}</h3>
      ${catItems.map(([name, data]) => {
        const qty = data.quantity ? `${parseFloat(data.quantity).toFixed(1)} ${data.unit || ''}`.trim() : '';
        return `<div class="shopping-item ${data.checked ? 'checked' : ''}" data-name="${name}">
          <input type="checkbox" class="item-check" data-name="${name}" ${data.checked ? 'checked' : ''}>
          <span class="item-label">${name}${qty ? ' — ' + qty : ''}</span>
          <button class="btn btn-secondary btn-sm pantry-btn" data-name="${name}" title="Add to pantry staples">☆</button>
        </div>`;
      }).join('')}
    </div>`;
  }

  return `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
      <h2>Shopping List — Week of ${weekLabel}</h2>
      <div style="display:flex;gap:0.5rem">
        <button class="btn btn-secondary" id="btn-export-md">Export Markdown</button>
        <button class="btn btn-primary" id="btn-regen">Regenerate</button>
      </div>
    </div>
    ${sections}`;
}

function bindShoppingEvents(week, sl) {
  document.getElementById('btn-regen')?.addEventListener('click', async () => {
    try {
      await api('POST', `/weeks/${week.id}/shopping-list`);
      renderShopping();
    } catch (e) { showError(e.message); }
  });

  document.getElementById('btn-export-md')?.addEventListener('click', async () => {
    try {
      const resp = await fetch(`/api/weeks/${week.id}/export`);
      if (!resp.ok) throw new Error(await resp.text());
      const text = await resp.text();
      const blob = new Blob([text], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `shopping-${week.week_start_date}.md`;
      a.click();
    } catch (e) { showError(e.message); }
  });

  document.querySelectorAll('.item-check').forEach(checkbox => {
    checkbox.addEventListener('change', async () => {
      const name = checkbox.dataset.name;
      const updated = { ...sl.items };
      updated[name] = { ...updated[name], checked: checkbox.checked };
      try {
        // Patch the shopping list items directly via week update
        sl.items = updated;
        checkbox.closest('.shopping-item').classList.toggle('checked', checkbox.checked);
      } catch (e) { showError(e.message); }
    });
  });

  document.querySelectorAll('.pantry-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const name = btn.dataset.name;
      const item = sl?.items?.[name] || {};
      try {
        await api('POST', '/pantry', { ingredient_name: name, category: item.category || 'other' });
        btn.textContent = '★';
        btn.title = 'Added to pantry';
      } catch (e) { showError(e.message); }
    });
  });
}
```

- [ ] Append to `app/static/style.css`:

```css
.shopping-section { margin-bottom: 1.5rem; }
.shopping-section h3 { margin-bottom: 0.5rem; border-bottom: 1px solid #ddd; padding-bottom: 0.25rem; }

.shopping-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid #f0f0f0;
}
.shopping-item.checked .item-label { text-decoration: line-through; color: #aaa; }
.item-label { flex: 1; }
.pantry-btn { color: #888; background: transparent; border: none; font-size: 1rem; }
.pantry-btn:hover { color: #333; }
```

Manual verification:
1. Generate a shopping list from planner view
2. Navigate to Shopping — items appear grouped by category
3. Check off an item — it gets struck through
4. Click ☆ on an item — adds to pantry staples (★ appears)
5. "Export Markdown" downloads a .md file

- [ ] `git commit -m "feat: shopping list view — grouped items, check-off, pantry quick-add, export"`

---

### Task 16: Settings View

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`

- [ ] Replace the `renderSettings` stub in `app/static/app.js` with the complete implementation:

```javascript
async function renderSettings() {
  const el = document.getElementById('view-settings');
  el.innerHTML = '<p>Loading...</p>';
  try {
    const [pantry, prefs] = await Promise.all([
      api('GET', '/pantry'),
      api('GET', '/preferences'),
    ]);
    el.innerHTML = settingsHTML(pantry, prefs);
    bindSettingsEvents();
  } catch (e) { showError(e.message); }
}

function settingsHTML(pantry, prefs) {
  const pantryRows = pantry.map(s =>
    `<div class="settings-item" data-id="${s.id}" data-type="pantry">
      <span>${s.ingredient_name} <small>(${s.category})</small></span>
      <button class="btn btn-danger btn-sm" data-action="delete-pantry" data-id="${s.id}">Remove</button>
    </div>`
  ).join('') || '<p style="color:#888;font-size:0.9rem">None yet.</p>';

  const prefRows = prefs.map(p =>
    `<div class="settings-item" data-id="${p.id}" data-type="pref">
      <span class="pref-badge pref-${p.type}">${p.type}</span>
      <span>${p.value} <small>(${p.scope})</small></span>
      <button class="btn btn-danger btn-sm" data-action="delete-pref" data-id="${p.id}">Remove</button>
    </div>`
  ).join('') || '<p style="color:#888;font-size:0.9rem">None yet.</p>';

  return `
    <h2 style="margin-bottom:1.5rem">Settings</h2>

    <section class="settings-section">
      <h3>Pantry Staples</h3>
      <p style="color:#666;font-size:0.9rem;margin-bottom:0.75rem">Ingredients always on hand — excluded from shopping lists.</p>
      <div class="settings-add-row">
        <input id="new-staple-name" placeholder="Ingredient name" style="flex:1">
        <select id="new-staple-cat">
          <option value="pantry">pantry</option>
          <option value="produce">produce</option>
          <option value="protein">protein</option>
          <option value="dairy">dairy</option>
          <option value="other">other</option>
        </select>
        <button class="btn btn-primary" id="btn-add-staple">Add</button>
      </div>
      <div id="pantry-list">${pantryRows}</div>
    </section>

    <section class="settings-section">
      <h3>Preferences</h3>
      <p style="color:#666;font-size:0.9rem;margin-bottom:0.75rem">Likes and dislikes used to weight meal suggestions.</p>
      <div class="settings-add-row">
        <input id="new-pref-value" placeholder="e.g. spicy, fish, Mediterranean" style="flex:1">
        <select id="new-pref-type">
          <option value="like">like</option>
          <option value="dislike">dislike</option>
        </select>
        <select id="new-pref-scope">
          <option value="ingredient">ingredient</option>
          <option value="cuisine">cuisine</option>
        </select>
        <button class="btn btn-primary" id="btn-add-pref">Add</button>
      </div>
      <div id="pref-list">${prefRows}</div>
    </section>`;
}

function bindSettingsEvents() {
  document.getElementById('btn-add-staple').addEventListener('click', async () => {
    const name = document.getElementById('new-staple-name').value.trim();
    const cat = document.getElementById('new-staple-cat').value;
    if (!name) return;
    try {
      await api('POST', '/pantry', { ingredient_name: name, category: cat });
      document.getElementById('new-staple-name').value = '';
      renderSettings();
    } catch (e) { showError(e.message); }
  });

  document.getElementById('btn-add-pref').addEventListener('click', async () => {
    const value = document.getElementById('new-pref-value').value.trim();
    const type = document.getElementById('new-pref-type').value;
    const scope = document.getElementById('new-pref-scope').value;
    if (!value) return;
    try {
      await api('POST', '/preferences', { type, value, scope });
      document.getElementById('new-pref-value').value = '';
      renderSettings();
    } catch (e) { showError(e.message); }
  });

  document.querySelectorAll('[data-action="delete-pantry"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await api('DELETE', `/pantry/${btn.dataset.id}`);
        renderSettings();
      } catch (e) { showError(e.message); }
    });
  });

  document.querySelectorAll('[data-action="delete-pref"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await api('DELETE', `/preferences/${btn.dataset.id}`);
        renderSettings();
      } catch (e) { showError(e.message); }
    });
  });
}
```

- [ ] Append to `app/static/style.css`:

```css
.settings-section {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}
.settings-section h3 { margin-bottom: 0.5rem; }

.settings-add-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  align-items: center;
}

.settings-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid #f0f0f0;
}
.settings-item:last-child { border-bottom: none; }
.settings-item span { flex: 1; }
.settings-item small { color: #888; }

.pref-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  flex: 0;
  white-space: nowrap;
}
.pref-like { background: #d4edda; color: #155724; }
.pref-dislike { background: #f8d7da; color: #721c24; }
```

Manual verification:
1. Navigate to Settings
2. Add a pantry staple — appears in list; generate a shopping list containing that ingredient — it's excluded
3. Add a like/dislike preference — appears with colored badge
4. Remove a staple or preference — disappears from list

- [ ] `git commit -m "feat: settings view — pantry staples and preferences management"`

---

### Task 17: Frontend Polish

**Files:**
- Modify: `app/static/style.css`
- Modify: `app/static/index.html`
- Modify: `app/static/app.js`

**Before starting this task**, invoke the `frontend-design` skill:

```
Use the frontend-design skill to review and improve the meal planner UI.
```

The frontend-design skill will guide visual polish decisions. After the skill session:
- [ ] Apply any approved CSS/layout changes to `app/static/style.css`
- [ ] Apply any approved HTML structure changes to `app/static/index.html`
- [ ] Apply any approved JS changes to `app/static/app.js`
- [ ] `git commit -m "style: frontend polish via frontend-design skill"`
