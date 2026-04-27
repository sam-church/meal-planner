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
