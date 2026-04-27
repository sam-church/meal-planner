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
