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
    data = request.get_json(silent=True) or {}
    if not data.get('week_start_date'):
        return jsonify({'error': 'week_start_date is required'}), 400

    try:
        week_start = date.fromisoformat(data['week_start_date'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

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
    wp = db.session.get(WeekPlan, week_id)
    if not wp:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(wp.to_dict())

@bp.route('/<int:week_id>', methods=['PUT'])
def update_week(week_id):
    wp = db.session.get(WeekPlan, week_id)
    if not wp:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json(silent=True) or {}
    if 'slots' in data:
        from app.services.suggestion_service import LEFTOVER_PAIRS
        slots = dict(data['slots'])
        for dinner_key, lunch_key in LEFTOVER_PAIRS.items():
            dinner_val = slots.get(dinner_key)
            if dinner_val and not str(dinner_val).startswith('leftover:'):
                dinner_recipe = db.session.get(Recipe, int(str(dinner_val)))
                if dinner_recipe and dinner_recipe.makes_leftovers and not slots.get(lunch_key):
                    slots[lunch_key] = f'leftover:{dinner_recipe.id}'
            elif not dinner_val:
                # Clear the paired lunch if it was a leftover reference
                if str(slots.get(lunch_key, '')).startswith('leftover:'):
                    del slots[lunch_key]
        wp.slots = slots
    if 'notes' in data:
        wp.notes = data['notes']
    db.session.commit()
    return jsonify(wp.to_dict())


@bp.route('/<int:week_id>/suggest', methods=['POST'])
def suggest(week_id):
    wp = db.session.get(WeekPlan, week_id)
    if not wp:
        return jsonify({'error': 'Not found'}), 404
    from app.services.suggestion_service import suggest_slots
    wp.slots = suggest_slots(wp)
    db.session.commit()
    return jsonify(wp.to_dict())

@bp.route('/<int:week_id>/shopping-list', methods=['POST'])
def generate_shopping_list(week_id):
    wp = db.session.get(WeekPlan, week_id)
    if not wp:
        return jsonify({'error': 'Not found'}), 404
    from app.services.shopping_service import generate_shopping_list as _generate
    sl = _generate(wp)
    return jsonify(sl.to_dict()), 201

@bp.route('/<int:week_id>/shopping-list', methods=['GET'])
def get_shopping_list(week_id):
    wp = db.session.get(WeekPlan, week_id)
    if not wp:
        return jsonify({'error': 'Not found'}), 404
    sl = ShoppingList.query.filter_by(week_plan_id=week_id).first()
    if not sl:
        return jsonify(None)
    return jsonify(sl.to_dict())

@bp.route('/<int:week_id>/export', methods=['GET'])
def export_markdown(week_id):
    wp = db.session.get(WeekPlan, week_id)
    if not wp:
        return jsonify({'error': 'Not found'}), 404
    sl = ShoppingList.query.filter_by(week_plan_id=week_id).first()
    if not sl:
        return jsonify({'error': 'No shopping list for this week. Generate one first.'}), 404
    from app.services.export_service import render_markdown
    md = render_markdown(sl, wp)
    return md, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@bp.route('/<int:week_id>/sync-calendar', methods=['POST'])
def sync_calendar(week_id):
    wp = db.session.get(WeekPlan, week_id)
    if not wp:
        return jsonify({'error': 'Not found'}), 404
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
        slots_with_recipes[slot_key] = db.session.get(Recipe, recipe_id)

    try:
        from app.services.calendar_service import sync_week
    except ModuleNotFoundError as e:
        return jsonify({'error': f'Missing dependency ({e}) — restart the server from the virtual environment: source venv/bin/activate && python run.py'}), 503

    try:
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
