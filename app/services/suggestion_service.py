import random
from datetime import date, timedelta
from app.database import db
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
        and 'hungryroot' not in (r.tags or [])
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
                    dinner_recipe = db.session.get(Recipe, recipe_id)
                    if dinner_recipe and dinner_recipe.makes_leftovers:
                        slots[slot_key] = f'leftover:{recipe_id}'
                        continue
            recipe = pick(available)
        else:
            recipe = pick(available)

        if recipe:
            slots[slot_key] = recipe.id

    return slots
