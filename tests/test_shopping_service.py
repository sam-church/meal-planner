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
