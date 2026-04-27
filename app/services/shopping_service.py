from datetime import datetime, timezone
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
        recipe = db.session.get(Recipe, recipe_id)
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
        existing.generated_at = datetime.now(timezone.utc)
        db.session.commit()
        return existing

    sl = ShoppingList(week_plan_id=week_plan.id, items=items, generated_at=datetime.now(timezone.utc))
    db.session.add(sl)
    db.session.commit()
    return sl
