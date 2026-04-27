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
        wp.slots = data['slots']
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
